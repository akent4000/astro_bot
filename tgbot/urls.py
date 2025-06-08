from django.views.generic import RedirectView
from AstroBot import settings
from django.urls import path
from .views import quiz_editor
from tgbot.views import home

app_name = 'tgbot'

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'favicon.ico')),
    path('', home, name='home'),
]