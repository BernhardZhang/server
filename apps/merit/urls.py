from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'rounds', views.MeritRoundViewSet, basename='merit-round')
router.register(r'evaluations', views.ContributionEvaluationViewSet, basename='merit-evaluation')
router.register(r'criteria', views.MeritCriteriaViewSet, basename='merit-criteria')
router.register(r'project-calculations', views.ProjectMeritCalculationViewSet, basename='project-merit-calculation')
router.register(r'task-assignments', views.TaskMeritAssignmentViewSet, basename='task-merit-assignment')
router.register(r'peer-reviews', views.PeerReviewViewSet, basename='peer-review')
router.register(r'calculation-results', views.MeritCalculationResultViewSet, basename='merit-calculation-result')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', views.merit_dashboard, name='merit-dashboard'),
    path('projects/<int:project_id>/summary/', views.project_merit_summary, name='project-merit-summary'),
]