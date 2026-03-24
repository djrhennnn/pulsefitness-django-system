from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('django-admin/', admin.site.urls),   # Django built-in admin kept at /django-admin/
    path('', include('fitness.urls')),         # All fitness app URLs at root
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
