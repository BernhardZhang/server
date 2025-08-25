from django.urls import path
from . import views

urlpatterns = [
    path('widgets/', views.DashboardWidgetListCreateView.as_view(), name='dashboard-widget-list-create'),
    path('widgets/<int:pk>/', views.DashboardWidgetDetailView.as_view(), name='dashboard-widget-detail'),
    path('widgets/<int:widget_id>/data/', views.widget_data, name='widget-data'),
    path('widgets/layout/', views.update_widget_layout, name='update-widget-layout'),
    path('preferences/', views.UserPreferenceView.as_view(), name='user-preferences'),
    path('overview/', views.dashboard_overview, name='dashboard-overview'),
]