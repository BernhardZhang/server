from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'rounds', views.MeritRoundViewSet, basename='merit-round')
router.register(r'evaluations', views.ContributionEvaluationViewSet, basename='merit-evaluation')
router.register(r'criteria', views.MeritCriteriaViewSet, basename='merit-criteria')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', views.merit_dashboard, name='merit-dashboard'),
    path('projects/<int:project_id>/summary/', views.project_merit_summary, name='project-merit-summary'),
]