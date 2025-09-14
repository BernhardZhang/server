from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tasks', views.TaskViewSet, basename='task')
router.register(r'logs', views.ProjectLogViewSet, basename='projectlog')
router.register(r'points', views.PointsViewSet, basename='points')
router.register(r'points-history', views.PointsHistoryViewSet, basename='pointshistory')
router.register(r'evaluations', views.PointsEvaluationViewSet, basename='pointsevaluation')
router.register(r'rating-sessions', views.RatingSessionViewSet, basename='ratingsession')
router.register(r'ratings', views.RatingViewSet, basename='rating')

# WISlab新增路由
router.register(r'wislab-projects', views.WislabProjectViewSet, basename='wislab-project')
router.register(r'wislab-membership', views.WislabMembershipViewSet, basename='wislab-membership')
router.register(r'task-assignments', views.TaskAssignmentViewSet, basename='task-assignment')

# 项目为核心的新功能路由
router.register(r'recruitments', views.MemberRecruitmentViewSet, basename='recruitment')
router.register(r'applications', views.MemberApplicationViewSet, basename='application')
router.register(r'revenues', views.ProjectRevenueViewSet, basename='revenue')
router.register(r'task-teams', views.TaskTeamViewSet, basename='task-team')

urlpatterns = [
    path('', views.ProjectListCreateView.as_view(), name='project-list-create'),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='project-detail'),
    path('<int:project_id>/join/', views.join_project, name='join-project'),
    path('join-by-code/', views.join_by_code, name='join-by-code'),
    path('<int:project_id>/generate-invite-code/', views.generate_invite_code, name='generate-invite-code'),
    path('<int:project_id>/add-member/', views.add_project_member, name='add-project-member'),
    path('<int:project_id>/leave/', views.leave_project, name='leave-project'),
    path('<int:project_id>/logs/', views.project_logs, name='project-logs'),
    path('<int:project_id>/logs/create/', views.create_manual_log, name='create-manual-log'),
    path('search-users/', views.search_users, name='search-users'),
    path('task-stats/', views.task_statistics, name='task-statistics'),
    path('points-summary/', views.user_points_summary, name='user-points-summary'),
    path('transfer-points/', views.transfer_points, name='transfer-points'),
    
    # WISlab新增路径
    path('wislab-dashboard/', views.wislab_dashboard, name='wislab-dashboard'),
    path('system-statistics/', views.system_statistics, name='system-statistics'),
    
    # 任务评估评分相关路径
    path('<int:project_id>/task-evaluation/', views.create_task_evaluation_session, name='create-task-evaluation'),
    path('evaluation/<int:evaluation_id>/submit-task-evaluation/', views.submit_task_based_evaluation, name='submit-task-evaluation'),
    
    # 评分功能路径
    path('rating-sessions/', views.RatingSessionViewSet.as_view({'get': 'list', 'post': 'create'}), name='rating-session-list'),
    path('rating-sessions/<int:pk>/', views.RatingSessionViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='rating-session-detail'),
    path('rating-sessions/<int:pk>/end/', views.end_rating_session, name='end-rating-session'),
    path('ratings/', views.RatingViewSet.as_view({'get': 'list', 'post': 'create'}), name='rating-list'),
    path('ratings/<int:pk>/', views.RatingViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='rating-detail'),
    
    # 公开访问API - 无需登录
    path('public-stats/', views.public_stats, name='public-stats'),
    path('public/', views.public_projects, name='public-projects'),
    path('public/<int:pk>/', views.public_project_detail, name='public-project-detail'),
    path('<int:pk>/tasks/public/', views.public_project_tasks, name='public-project-tasks'),
    
    path('', include(router.urls)),
    path('hall/', views.project_hall_list, name='project-hall-list'),
]