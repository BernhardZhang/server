from django.urls import path
from . import views

urlpatterns = [
    path('records/', views.PointsRecordListView.as_view(), name='points-record-list'),
    path('transactions/', views.PointsTransactionListCreateView.as_view(), name='points-transaction-list-create'),
    path('rewards/', views.PointsRewardListView.as_view(), name='points-reward-list'),
    path('redemptions/', views.PointsRedemptionListCreateView.as_view(), name='points-redemption-list-create'),
    path('summary/', views.my_points_summary, name='my-points-summary'),
    path('transfer/', views.transfer_points, name='transfer-points'),
    path('rewards/available/', views.available_rewards, name='available-rewards'),
]