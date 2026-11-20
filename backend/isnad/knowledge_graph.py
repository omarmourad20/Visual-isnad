import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import AllowAny
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.response import Response

from .kg_converter import convert_kg_chain

KNOWLEDGE_GRAPH_URL = os.environ.get(
    "HADITH_KG_API_URL",
    "http://127.0.0.1:8077"
).rstrip("/")


class KnowledgeGraphJSONRenderer(JSONRenderer):
    # The JSON body is already UTF-8. Declare it for clients that use
    # a legacy decoding fallback when the response omits the charset.
    charset = "utf-8"


@api_view(["GET"])
@renderer_classes([KnowledgeGraphJSONRenderer, BrowsableAPIRenderer])
@permission_classes([AllowAny])
def knowledge_graph_hadith(request, hadith_id):
    url = f"{KNOWLEDGE_GRAPH_URL}/api/hadith/{hadith_id}"

    try:
        with urlopen(url, timeout=15) as response:
            data = json.load(response)

        if not isinstance(data, dict):
            raise ValueError("Expected a Knowledge Graph hadith object")
        data["visual_isnad_chains"] = [
            convert_kg_chain(sanad)
            for sanad in data.get("sanads", [])
        ]

        return Response(data)

    except HTTPError as error:
        if error.code == 404:
            return Response(
                {"error": "Hadith not found"},
                status=404
            )

        return Response(
            {"error": "Knowledge Graph API error"},
            status=502
        )

    except (URLError, TimeoutError, ValueError, KeyError, TypeError, AttributeError):
        return Response(
            {"error": "Knowledge Graph API unavailable"},
            status=502
        )


@api_view(["GET"])
@renderer_classes([KnowledgeGraphJSONRenderer, BrowsableAPIRenderer])
@permission_classes([AllowAny])
def knowledge_graph_rawi(request, rawi_id):
    url = f"{KNOWLEDGE_GRAPH_URL}/api/rawi/{rawi_id}"

    try:
        with urlopen(url, timeout=15) as response:
            data = json.load(response)

        if not isinstance(data, dict):
            raise ValueError("Expected a Knowledge Graph narrator object")
        return Response(data)

    except HTTPError as error:
        if error.code == 404:
            return Response(
                {"error": "Narrator not found"},
                status=404
            )

        return Response(
            {"error": "Knowledge Graph API error"},
            status=502
        )

    except (URLError, TimeoutError, ValueError):
        return Response(
            {"error": "Knowledge Graph API unavailable"},
            status=502
        )
