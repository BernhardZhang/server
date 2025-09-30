from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password_view, name='change-password'),
    path('users/', views.UserListView.as_view(), name='user-list'),
    # 第三方登录接口 - 按照官方文档格式
    path('sso/login', views.sso_login_view, name='sso-login'),
    path('sso/register', views.sso_register_view, name='sso-register'),
    path('sso/reset-password', views.sso_reset_password_view, name='sso-reset-password'),
    path('sso/success', views.sso_success_view, name='sso-success'),
]