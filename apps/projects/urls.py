from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'logs', views.ProjectLogViewSet, basename='projectlog')
router.register(r'recruitments', views.MemberRecruitmentViewSet, basename='recruitment')
router.register(r'applications', views.MemberApplicationViewSet, basename='application')
router.register(r'revenues', views.ProjectRevenueViewSet, basename='revenue')
router.register(r'distributions', views.RevenueDistributionViewSet, basename='distribution')
router.register(r'memberships', views.ProjectMembershipViewSet, basename='membership')

urlpatterns = [
    path('', views.ProjectListCreateView.as_view(), name='project-list-create'),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='project-detail'),
    path('join/', views.join_project, name='join-project'),
    path('leave/', views.leave_project, name='leave-project'),
    path('update-member-role/', views.update_member_role, name='update-member-role'),
    path('remove-member/', views.remove_member, name='remove-member'),
    path('update-contribution/', views.update_contribution, name='update-contribution'),
    path('my-projects/', views.my_projects, name='my-projects'),
    path('public/', views.public_projects, name='public-projects'),
    path('distribute-revenue/', views.distribute_revenue, name='distribute-revenue'),

    path('', include(router.urls)),
]