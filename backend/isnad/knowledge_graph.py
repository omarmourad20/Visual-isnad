"""Read-only Knowledge Graph proxy for Bukhari text and narrator profiles."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from django.conf import settings
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import AllowAny
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.response import Response

from .collection_scope import KG_BUKHARI_BOOK_ID

MAX_RESPONSE = 8 * 1024 * 1024


class KnowledgeGraphJSONRenderer(JSONRenderer):
    # Explicit for clients with a legacy decoding fallback.
    charset = "utf-8"


def fetch_record(kind, native_id):
    url = f'{settings.HADITH_KG_API_URL.rstrip("/")}/api/{kind}/{native_id}'
    with urlopen(url, timeout=8) as response:
        body = response.read(MAX_RESPONSE + 1)
    if len(body) > MAX_RESPONSE:
        raise ValueError("Knowledge Graph response too large")
    data = json.loads(body)
    if not isinstance(data, dict):
        raise ValueError("Expected a Knowledge Graph object")
    identity_field = "hadithId" if kind == "hadith" else "rawiId"
    if identity_field in data and str(data[identity_field]) != str(native_id):
        raise ValueError("Knowledge Graph returned a different record")
    return data


def unavailable(error, label):
    if isinstance(error, HTTPError):
        code = error.code
        error.close()
        if code == 404:
            return Response({"error": f"{label} not found"}, status=404)
    return Response({"error": "Knowledge Graph API unavailable"}, status=502)


UPSTREAM_ERRORS = (URLError, OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError)


@api_view(["GET"])
@renderer_classes([KnowledgeGraphJSONRenderer, BrowsableAPIRenderer])
@permission_classes([AllowAny])
def knowledge_graph_hadith(request, hadith_id):
    try:
        data = fetch_record("hadith", hadith_id)
        if str(data.get("bookId")) != KG_BUKHARI_BOOK_ID:
            return Response({"error": "Sahih al-Bukhari hadith not found"}, status=404)
        # A book identifier confirms collection membership, but the upstream
        # sanads have not been individually reviewed for graph use.
        return Response({
            "hadithId": hadith_id,
            **{key: data[key] for key in ("bookId", "noInBook", "nass", "matnClean") if key in data},
        })
    except UPSTREAM_ERRORS as error:
        return unavailable(error, "Hadith")


@api_view(["GET"])
@renderer_classes([KnowledgeGraphJSONRenderer, BrowsableAPIRenderer])
@permission_classes([AllowAny])
def knowledge_graph_rawi(request, rawi_id):
    try:
        return Response(fetch_record("rawi", rawi_id))
    except UPSTREAM_ERRORS as error:
        return unavailable(error, "Narrator")
