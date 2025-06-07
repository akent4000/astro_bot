from django.views.generic import RedirectView
from AstroBot import settings
from django.urls import path
app_name = 'tgbot'

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'favicon.ico')),
]