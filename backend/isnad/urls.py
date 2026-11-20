from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import HadithViewSet, NarratorViewSet, TransmissionEdgeViewSet, auth_login, auth_logout, auth_me
from .knowledge_graph import knowledge_graph_hadith, knowledge_graph_rawi

router = DefaultRouter()
router.register("narrators", NarratorViewSet)
router.register("hadiths", HadithViewSet)
router.register("edges", TransmissionEdgeViewSet)

urlpatterns = [
    path("auth/me/", auth_me),
    path("auth/login/", auth_login),
    path("auth/logout/", auth_logout),

    # Hadith Knowledge Graph API
    path(
        "knowledge-graph/hadiths/<int:hadith_id>/",
        knowledge_graph_hadith,
        name="knowledge-graph-hadith",
    ),
    # Knowledge Graph narrator details
    path(
        "knowledge-graph/rawis/<int:rawi_id>/",
        knowledge_graph_rawi,
        name="knowledge-graph-rawi",
    ),

    path("", include(router.urls)),
]