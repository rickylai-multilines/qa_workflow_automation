"""
URL configuration for qa_workflow project.
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

def _redirect_admin_wip(request):
    """Redirect /admin/wip/ to orders-workflow WIP management page."""
    return redirect('orders:wip-admin', permanent=False)

urlpatterns = [
    path('admin/wip/', _redirect_admin_wip),
    path('admin/', admin.site.urls),
    path('', include('qa_app.urls')),
    path('orders-workflow/', include('orders.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

