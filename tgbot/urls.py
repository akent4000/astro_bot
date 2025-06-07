from django.views.generic import RedirectView
from AstroBot import settings
from django.urls import path
from .views import quiz_editor

app_name = 'tgbot'

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'favicon.ico')),
    path('editor/quiz/new/', quiz_editor, name='quiz_create'),
    path('editor/quiz/<int:pk>/edit/', quiz_editor, name='quiz_edit'),
]