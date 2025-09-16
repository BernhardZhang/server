from django.urls import path
from . import views

urlpatterns = [
    path('rounds/', views.VotingRoundListCreateView.as_view(), name='voting-round-list-create'),
    path('rounds/active/', views.ActiveVotingRoundView.as_view(), name='active-voting-round'),
    path('rounds/<int:round_id>/activate/', views.activate_round, name='activate-round'),
    path('votes/', views.VoteListCreateView.as_view(), name='vote-list-create'),
    path('votes/<int:pk>/', views.VoteDetailView.as_view(), name='vote-detail'),
    path('votes/my/', views.my_votes, name='my-votes'),
    path('votes/received/', views.votes_received, name='votes-received'),
    path('evaluations/', views.ContributionEvaluationListCreateView.as_view(), name='evaluation-list-create'),
    path('evaluations/<int:pk>/', views.ContributionEvaluationDetailView.as_view(), name='evaluation-detail'),
    path('self-evaluations/', views.SelfEvaluationListCreateView.as_view(), name='self-evaluation-list-create'),
    path('self-evaluations/<int:pk>/', views.SelfEvaluationDetailView.as_view(), name='self-evaluation-detail'),

    # 评分活动相关URLs
    path('rating-sessions/', views.RatingSessionListCreateView.as_view(), name='rating-session-list-create'),
    path('rating-sessions/<int:pk>/', views.RatingSessionDetailView.as_view(), name='rating-session-detail'),
    path('rating-sessions/my/', views.my_rating_sessions, name='my-rating-sessions'),

    # 评分记录相关URLs
    path('ratings/', views.RatingListCreateView.as_view(), name='rating-list-create'),
    path('ratings/my/', views.MyRatingsView.as_view(), name='my-ratings'),
    path('ratings/received/', views.RatingsReceivedView.as_view(), name='ratings-received'),
]