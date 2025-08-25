from django.urls import path
from . import views

urlpatterns = [
    path('', views.TaskListCreateView.as_view(), name='task-list-create'),
    path('<int:pk>/', views.TaskDetailView.as_view(), name='task-detail'),
    path('<int:task_id>/comments/', views.TaskCommentListCreateView.as_view(), name='task-comment-list-create'),
    path('<int:task_id>/attachments/', views.TaskAttachmentListView.as_view(), name='task-attachment-list'),
    path('<int:task_id>/attachments/upload/', views.TaskAttachmentUploadView.as_view(), name='task-attachment-upload'),
    path('attachments/<int:pk>/delete/', views.TaskAttachmentDeleteView.as_view(), name='task-attachment-delete'),
    path('<int:task_id>/logs/', views.TaskLogListView.as_view(), name='task-log-list'),
    path('<int:task_id>/user-logs/', views.TaskUserLogListCreateView.as_view(), name='task-user-log-list-create'),
    path('user-logs/<int:pk>/', views.TaskUserLogDetailView.as_view(), name='task-user-log-detail'),
    path('user-logs/<int:log_id>/upload-attachment/', views.upload_task_user_log_attachment, name='upload-task-user-log-attachment'),
    path('<int:task_id>/summary/', views.task_summary_with_logs, name='task-summary-with-logs'),
    path('<int:task_id>/status/', views.update_task_status, name='update-task-status'),
    path('<int:task_id>/evaluate/', views.evaluate_task, name='evaluate-task'),
    path('<int:task_id>/evaluations/', views.task_evaluation_list, name='task-evaluation-list'),
    path('<int:task_id>/claim/', views.claim_task, name='claim-task'),
    path('summary/', views.my_task_summary, name='my-task-summary'),
    path('score-summary/', views.user_task_score_summary, name='user-task-score-summary'),
    path('hall/', views.task_hall_list, name='task-hall-list'),
    
    # 评估会话相关
    path('evaluation-sessions/', views.TaskEvaluationSessionListCreateView.as_view(), name='evaluation-session-list-create'),
    path('evaluation-sessions/<int:pk>/', views.TaskEvaluationSessionDetailView.as_view(), name='evaluation-session-detail'),
    path('evaluation-sessions/<int:session_id>/submit/', views.submit_batch_task_evaluation, name='submit-batch-evaluation'),
    path('evaluation-sessions/<int:session_id>/complete/', views.complete_evaluation_session, name='complete-evaluation-session'),
    path('evaluation-sessions/<int:session_id>/summary/', views.evaluation_session_summary, name='evaluation-session-summary'),
    
    # 功分计算相关
    path('<int:task_id>/merit-calculation/', views.task_merit_calculation, name='task-merit-calculation'),
    path('<int:task_id>/merit-calculation/finalize/', views.finalize_merit_calculation, name='finalize-merit-calculation'),
    path('<int:task_id>/contribution-records/', views.task_contribution_records, name='task-contribution-records'),
    path('merit-summary/', views.user_merit_summary, name='user-merit-summary'),
]