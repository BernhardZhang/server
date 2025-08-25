from django.urls import path
from . import views

urlpatterns = [
    path('reports/', views.FinancialReportListCreateView.as_view(), name='financial-report-list-create'),
    path('reports/generate/', views.generate_financial_report, name='generate-financial-report'),
    path('reports/<int:report_id>/authorize/', views.authorize_report, name='authorize-report'),
    path('transactions/', views.TransactionListView.as_view(), name='transaction-list'),
    path('equity/', views.ShareholderEquityListView.as_view(), name='equity-list'),
    path('equity/real/', views.get_real_equity_holdings, name='real-equity-holdings'),
    path('portfolio/', views.my_portfolio, name='my-portfolio'),
    path('payment/wechat/', views.create_wechat_payment, name='wechat-payment'),
]