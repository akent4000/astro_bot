from django.views.generic import RedirectView
from AstroBot import settings
from django.urls import include, path
from django.contrib import admin
app_name = 'tgbot'

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'favicon.ico')),
    path('admin_tools/', include('admin_tools.urls')),
    path('admin/', admin.site.urls),
]