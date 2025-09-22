from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'recruitments', views.MemberRecruitmentViewSet, basename='recruitment')
router.register(r'applications', views.MemberApplicationViewSet, basename='application')
router.register(r'revenues', views.ProjectRevenueViewSet, basename='revenue')
router.register(r'distributions', views.RevenueDistributionViewSet, basename='distribution')
router.register(r'memberships', views.ProjectMembershipViewSet, basename='membership')

urlpatterns = [
    path('', views.ProjectListCreateView.as_view(), name='project-list-create'),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='project-detail'),
    path('<int:project_id>/logs/', views.get_project_logs, name='project-logs'),
    path('<int:project_id>/logs/create/', views.create_project_log, name='create-project-log'),
    path('join/', views.join_project, name='join-project'),
    path('join-by-code/', views.join_by_code, name='join-by-code'),
    path('<int:project_id>/generate-invite-code/', views.generate_invite_code, name='generate-invite-code'),
    path('leave/', views.leave_project, name='leave-project'),
    path('update-member-role/', views.update_member_role, name='update-member-role'),
    path('remove-member/', views.remove_member, name='remove-member'),
    # 新增REST风格的URL模式以匹配前端调用（使用user_id）
    path('<int:project_id>/members/<int:user_id>/set-admin/', views.set_member_admin, name='set-member-admin'),
    path('<int:project_id>/members/<int:user_id>/remove-admin/', views.remove_member_admin, name='remove-member-admin'),
    path('<int:project_id>/members/<int:user_id>/remove/', views.remove_project_member, name='remove-project-member'),
    path('update-contribution/', views.update_contribution, name='update-contribution'),
    path('my-projects/', views.my_projects, name='my-projects'),
    path('public/', views.public_projects, name='public-projects'),
    path('distribute-revenue/', views.distribute_revenue, name='distribute-revenue'),
    path('project-points/', views.project_points, name='project-points'),

    path('', include(router.urls)),
]