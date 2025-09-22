from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.users.urls')),
    path('api/projects/', include('apps.projects.urls')),
    path('api/voting/', include('apps.voting.urls')),
    path('api/merit/', include('apps.merit.urls')),
    path('api/finance/', include('apps.finance.urls')),
    path('api/points/', include('apps.points.urls')),
    path('api/tasks/', include('apps.tasks.urls')),
    path('api/analysis/', include('apps.analysis.urls')),
    path('api/logs/', include('apps.logs.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)