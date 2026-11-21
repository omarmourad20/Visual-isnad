import re
from collections import defaultdict

from django.http import Http404
from django.core.cache import cache
from django.db.models import Case, Count, F, Q, TextField, Value, When
from django.db.models.functions import Left, Replace
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from rawis_catalog import UNRESOLVED_NARRATOR_ID_START

from .bukhari_books import BUKHARI_BOOKS
from .collection_scope import BUKHARI_TITLES
from .editor_auth import issue_editor_token
from .permissions import StaffWritePermission
from .throttles import LoginRateThrottle
from .models import Hadith, Narrator, TransmissionEdge
from .edge_schema import has_chain_index
from .reviewed_routes import (
    apply_path_identity_review, correct_reviewed_legacy_route, describe_reviewed_routes,
    ibn_ulayya_supplement, route_evidence, supplemental_profile, withheld_route_reason,
)
from .source_api import source_candidates
from .serializers import (
    COMPACT_NARRATOR_FIELDS,
    CompactNarratorSerializer,
    HadithListSerializer,
    HadithSerializer,
    NarratorSerializer,
    LegacyTransmissionEdgeSerializer,
    TransmissionEdgeSerializer,
)

BOOKS_CACHE_KEY = "hadith_books_catalog"
COMPACT_TRUE = {"1", "true", "yes"}

BOOK_REF_RE = re.compile(r"Book\s+(\d+)", re.I)

ARABIC_SEARCH_MARKS = "ًٌٍَُِّْٰـ"
ARABIC_SEARCH_MARKS_TABLE = str.maketrans("", "", ARABIC_SEARCH_MARKS)
ARABIC_LETTER_RE = re.compile(r"[ء-ي]")


def without_arabic_search_marks(field):
    expression = F(field)
    for mark in ARABIC_SEARCH_MARKS:
        expression = Replace(expression, Value(mark), Value(""), output_field=TextField())
    return expression



def bukhari_hadiths():
    return Hadith.objects.filter(book_title__in=BUKHARI_TITLES)


def hadith_by_pk(hadith_ref: str | None) -> Hadith | None:
    if not hadith_ref or not str(hadith_ref).isdecimal():
        return None
    return bukhari_hadiths().filter(pk=hadith_ref).first()


def hadith_by_number(hadith_ref: str | None) -> Hadith | None:
    if not hadith_ref:
        return None
    return bukhari_hadiths().filter(hadith_number=str(hadith_ref)).first()


def resolve_hadith_lookup(lookup: str | None) -> Hadith | None:
    """Detail URLs: printed Bukhari number first, then database pk."""
    return hadith_by_number(lookup) or hadith_by_pk(lookup)


def chain_payload(hadith: Hadith) -> dict:
    queryset = TransmissionEdge.objects.filter(hadith=hadith).order_by("sequence", "id")
    indexed_schema = has_chain_index(queryset.db)
    serializer = TransmissionEdgeSerializer if indexed_schema else LegacyTransmissionEdgeSerializer
    if not indexed_schema:
        queryset = queryset.defer("chain_index")
    edges = list(queryset)
    raw_edges = serializer(edges, many=True).data
    display_edges = correct_reviewed_legacy_route(hadith, raw_edges)
    if display_edges is raw_edges:
        display_edges = apply_path_identity_review(hadith, raw_edges)
    narrator_ids = {edge[field] for edge in display_edges for field in ("teacher", "student")}
    narrators = list(Narrator.objects.filter(id__in=narrator_ids).only(*COMPACT_NARRATOR_FIELDS))
    if display_edges is not raw_edges:
        stored_ids = {person.pk for person in narrators}
        # Only the documented supplemental narrator can be absent in the legacy catalog.
        for narrator_id in narrator_ids - stored_ids:
            profile = supplemental_profile(narrator_id)
            if profile is not None:
                narrators.append(profile)
        if {person.pk for person in narrators} != narrator_ids:
            display_edges = raw_edges
            original_ids = {edge[field] for edge in raw_edges for field in ("teacher", "student")}
            narrators = list(Narrator.objects.filter(id__in=original_ids).only(*COMPACT_NARRATOR_FIELDS))
    return {
        "narrators": CompactNarratorSerializer(narrators, many=True).data,
        "edges": display_edges,
        "withheld_route_reason": withheld_route_reason(hadith, raw_edges),
        "reviewed_routes": describe_reviewed_routes(hadith, raw_edges, display_edges),
        "chain_index_available": indexed_schema,
        "chain_boundaries_recorded": indexed_schema and all(edge.chain_index is not None for edge in edges),
    }


def book_catalog() -> list[dict]:
    cached = cache.get(BOOKS_CACHE_KEY)
    if cached is not None:
        return cached

    counted = list(
        bukhari_hadiths().exclude(book_number=None)
        .values("book_number")
        .annotate(count=Count("id"))
        .order_by("book_number")
    )
    counts: dict[int, int] = {int(row["book_number"]): int(row["count"]) for row in counted}

    if not counts:
        fallback: dict[int, int] = defaultdict(int)
        for ref in bukhari_hadiths().values_list("in_book_reference", flat=True).iterator(chunk_size=2000):
            match = BOOK_REF_RE.search(ref or "")
            if match:
                fallback[int(match.group(1))] += 1
        counts = fallback

    catalog = []
    for number in sorted(counts):
        title, arabic = BUKHARI_BOOKS.get(number, (f"Book {number}", ""))
        catalog.append(
            {
                "number": number,
                "title": title,
                "title_arabic": arabic,
                "count": counts[number],
            }
        )
    cache.set(BOOKS_CACHE_KEY, catalog, 60 * 60)
    return catalog


def staff_session_payload(user):
    if not user.is_authenticated:
        return {"authenticated": False, "can_edit_biographies": False, "username": "", "initials": ""}
    name = user.get_username()
    parts = [part for part in name.replace(".", " ").replace("_", " ").split() if part]
    initials = (parts[0][:2] if len(parts) == 1 else f"{parts[0][0]}{parts[1][0]}").upper() if parts else "ED"
    return {
        "authenticated": True,
        "can_edit_biographies": bool(user.is_staff),
        "username": name,
        "initials": initials,
    }


def auth_payload(request, user, token=""):
    payload = staff_session_payload(user)
    # The editor page cannot read a CSRF cookie set by the API host.
    payload["csrfToken"] = get_token(request)
    if token:
        payload["token"] = token
    return payload


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def auth_me(request):
    return Response(auth_payload(request, request.user))


@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])
@throttle_classes([LoginRateThrottle])
def auth_login(request):
    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_staff or not user.is_active:
        return Response({"detail": "Staff username and password required."}, status=403)
    login(request, user)
    return Response(auth_payload(request, user, issue_editor_token(user)))


@api_view(["POST"])
@permission_classes([AllowAny])
def auth_logout(request):
    logout(request)
    return Response(auth_payload(request, request.user))


class NarratorViewSet(viewsets.ModelViewSet):
    queryset = Narrator.objects.all()
    serializer_class = NarratorSerializer
    permission_classes = [StaffWritePermission]

    def get_serializer_class(self):
        if self.action == "list":
            return CompactNarratorSerializer
        return NarratorSerializer

    def retrieve(self, request, *args, **kwargs):
        try:
            narrator = self.get_object()
        except Http404:
            narrator = supplemental_profile(self.kwargs[self.lookup_field])
            if narrator is None:
                raise
        data = self.get_serializer(narrator).data
        if narrator._state.adding:
            data["profile_source"] = ibn_ulayya_supplement()["source"]
            data["catalog_source_url"] = data["profile_source"]
        elif narrator.pk == 20020:
            data["catalog_source_url"] = "https://muslimscholars.info/manage.php?ID=20020&submit=scholar"
            # The profile audit corroborated the identity across the catalogs.
            data["knowledge_graph_profile"] = {
                "id": 1003795, "name": None, "arabic_name": "شعبة بن الحجاج بن الورد",
            }

        def related_ids(field):
            ids = []
            for token in field.split(","):
                token = token.strip()
                if token.isascii() and token.isdecimal() and len(token) <= 10:
                    narrator_id = int(token)
                    if 0 < narrator_id <= 2_147_483_647:
                        ids.append(narrator_id)
            return list(dict.fromkeys(ids))

        teachers = related_ids(narrator.teachers_inds)
        students = related_ids(narrator.students_inds)
        # Keep imported graph evidence separate from the catalog's own
        # student list. Synthetic unresolved IDs are not named students.
        transmission_students = list(
            TransmissionEdge.objects.filter(
                hadith__book_title__in=BUKHARI_TITLES,
                teacher=narrator, student_id__lt=UNRESOLVED_NARRATOR_ID_START,
            )
            .exclude(student_id=narrator.pk)
            .order_by("student_id")
            .values_list("student_id", flat=True)
            .distinct()
        )
        references = Narrator.objects.only("id", "name", "arabic_name").in_bulk(
            set(teachers) | set(students) | set(transmission_students)
        )

        def summarize(ids):
            return [
                {
                    "id": narrator_id,
                    "name": references[narrator_id].name if narrator_id in references else None,
                    "arabic_name": references[narrator_id].arabic_name if narrator_id in references else None,
                }
                for narrator_id in ids
            ]

        data["teachers"] = summarize(teachers)
        data["students"] = summarize(students)
        data["transmission_students"] = summarize(transmission_students)
        if request.query_params.get("evidence") == "1":
            links = []
            candidates = [url for url, review in route_evidence().items() if review.get("lengths")]
            for hadith in bukhari_hadiths().filter(reference_url__in=candidates).order_by("id"):
                payload = chain_payload(hadith)
                relevant_ids = {
                    edge["id"] for edge in payload["edges"] if narrator.pk in (edge["student"], edge["teacher"])
                }
                reviewed_edge_id = next((
                    edge_id for route in payload["reviewed_routes"] if route["status"] == "reviewed"
                    for edge_id in route["edge_ids"] if edge_id in relevant_ids
                ), None)
                if reviewed_edge_id is not None:
                    links.append({"id": hadith.pk, "hadith_number": hadith.hadith_number,
                                  "reference_url": hadith.reference_url, "edge_id": reviewed_edge_id})
            data["reviewed_bukhari_hadiths"] = links
        return Response(data)

    def get_queryset(self):
        queryset = super().get_queryset().order_by("id")
        if self.action == "list":
            queryset = queryset.only(*COMPACT_NARRATOR_FIELDS)
        search = self.request.query_params.get("search")
        hadith_number = self.request.query_params.get("hadith_number")
        hadith_id = self.request.query_params.get("hadith_id")
        hadith = hadith_by_number(hadith_number) if hadith_number else hadith_by_pk(hadith_id)
        if (hadith_number or hadith_id) and hadith is None:
            return queryset.none()
        if hadith:
            edge_qs = TransmissionEdge.objects.filter(hadith=hadith)
            narrator_ids = set(edge_qs.values_list("teacher_id", flat=True)) | set(
                edge_qs.values_list("student_id", flat=True)
            )
            queryset = queryset.filter(id__in=narrator_ids)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(arabic_name__icontains=search)
                | Q(aliases__icontains=search)
            )
        return queryset


class FlexiblePagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 400


class HadithViewSet(viewsets.ModelViewSet):
    queryset = Hadith.objects.order_by("id")
    serializer_class = HadithSerializer
    pagination_class = FlexiblePagination
    permission_classes = [StaffWritePermission]

    def get_object(self):
        lookup = self.kwargs.get(self.lookup_field)
        hadith = resolve_hadith_lookup(lookup)
        if hadith is None:
            raise NotFound("Hadith not found.")
        return hadith

    def get_serializer_class(self):
        compact = self.request.query_params.get("compact")
        if self.action == "list" and compact in {"1", "true", "yes"}:
            return HadithListSerializer
        return HadithSerializer

    def get_queryset(self):
        queryset = bukhari_hadiths().order_by("id")
        search = self.request.query_params.get("search")
        number = self.request.query_params.get("hadith_number")
        book = self.request.query_params.get("book")
        compact = self.request.query_params.get("compact") in COMPACT_TRUE
        if number:
            queryset = queryset.filter(hadith_number=number)
        if book and str(book).isdigit():
            queryset = queryset.filter(
                Q(book_number=int(book)) | Q(in_book_reference__startswith=f"Book {book},")
            )
        elif book:
            queryset = queryset.filter(in_book_reference__startswith=f"Book {book},")
        if search:
            matches = (
                Q(hadith_number__icontains=search)
                | Q(topic__icontains=search)
                | Q(chapter_title__icontains=search)
                | Q(english_matn__icontains=search)
            )
            if ARABIC_LETTER_RE.search(search):
                unvocalized = search.translate(ARABIC_SEARCH_MARKS_TABLE)
                queryset = queryset.alias(
                    searchable_arabic_title=without_arabic_search_marks("chapter_title_arabic"),
                    searchable_arabic_matn=without_arabic_search_marks("arabic_matn"),
                )
                matches |= (
                    Q(searchable_arabic_title__icontains=unvocalized)
                    | Q(searchable_arabic_matn__icontains=unvocalized)
                )
            queryset = queryset.filter(matches).order_by(
                Case(When(hadith_number__iexact=search, then=Value(0)), default=Value(1)),
                "id",
            )
        if self.action == "list" and compact:
            queryset = queryset.defer(
                "arabic_isnad",
                "arabic_matn",
                "arabic_full",
                "reference_url",
            ).annotate(_preview=Left("english_matn", 80))
        return queryset

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        data = HadithSerializer(instance).data
        if request.query_params.get("chain") in COMPACT_TRUE:
            data.update(chain_payload(instance))
        return Response(data)

    @action(detail=True, methods=["get"], url_path="sources")
    def sources(self, request, *args, **kwargs):
        state, candidates = source_candidates(self.get_object())
        if state != "available":
            return Response({"count": 0, "next": None, "previous": None, "results": [], "status": state})
        response = self.get_paginated_response(self.paginate_queryset(candidates))
        response.data["status"] = "available"
        return response

    @action(detail=True, methods=["get"], url_path="source-routes")
    def source_routes(self, request, *args, **kwargs):
        self.get_object()
        return Response({"error": "No reviewed external routes are available"}, status=404)

    @action(detail=False, methods=["get"], url_path="books")
    def books(self, request):
        return Response(book_catalog())

    @action(detail=False, methods=["get"], url_path="bootstrap")
    def bootstrap(self, request):
        books = book_catalog()
        first = (
            bukhari_hadiths().filter(hadith_number="1").first()
            or bukhari_hadiths().order_by("id").first()
        )
        if first is None:
            return Response({"books": books, "hadith": None, "narrators": [], "edges": []})
        payload = HadithSerializer(first).data
        chain = chain_payload(first)
        payload.update(chain)
        return Response({"books": books, "hadith": payload, **chain})


class TransmissionEdgeViewSet(viewsets.ModelViewSet):
    queryset = TransmissionEdge.objects.order_by("id")
    serializer_class = TransmissionEdgeSerializer
    permission_classes = [StaffWritePermission]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.indexed_schema = has_chain_index(self.queryset.db)
        if not self.indexed_schema and request.method not in {"GET", "HEAD", "OPTIONS"}:
            from rest_framework.exceptions import APIException

            error = APIException("Transmission edge editing requires the chain_index schema.")
            error.status_code = 409
            raise error

    def get_serializer_class(self):
        return TransmissionEdgeSerializer if self.indexed_schema else LegacyTransmissionEdgeSerializer

    def get_queryset(self):
        queryset = super().get_queryset().filter(hadith__book_title__in=BUKHARI_TITLES)
        if not self.indexed_schema:
            queryset = queryset.defer("chain_index")
        hadith_number = self.request.query_params.get("hadith_number")
        hadith_id = self.request.query_params.get("hadith_id")
        hadith = hadith_by_number(hadith_number) if hadith_number else hadith_by_pk(hadith_id)
        if hadith_number or hadith_id:
            if hadith is None:
                return queryset.none()
            queryset = queryset.filter(hadith=hadith).order_by("sequence", "id")
        return queryset
