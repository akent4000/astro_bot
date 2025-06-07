# tgbot/admin/quiz.py
import nested_admin
from django.contrib import admin
from django.db import models
from django.utils import timezone
from tgbot.models import (
    QuizTopic,
    QuizLevel,
    Quiz,
    Question,
    Choice,
    UserQuizSession,
    UserQuizAnswer,
)
from django.utils.html import format_html
from django.forms import TextInput, Textarea


##############################
# QuizTopic Admin
##############################
@admin.register(QuizTopic)
class QuizTopicAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title",)


##############################
# QuizLevel Admin
##############################
@admin.register(QuizLevel)
class QuizLevelAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title",)



class ChoiceInline(nested_admin.NestedTabularInline):
    model = Choice
    extra = 1
    sortable_field_name = 'order'
    fields = ('text', 'is_correct', 'order',)
    formfield_overrides = {
        # делаем поле текста компактнее
        models.CharField: {'widget': TextInput(attrs={'size': '40'})},
    }

class QuestionInline(nested_admin.NestedTabularInline):
    css = {'all': ('admin/css/quiz_compact.css',)}
    model = Question
    inlines = [ChoiceInline]           # вложаем табличный инлайн
    extra = 1
    sortable_field_name = 'order'
    # показываем в одной строке: текст вопроса и порядок,
    # а пояснение складываем в сворачиваемый блок
    fieldsets = (
        (None, {
            'fields': ('text', 'order'),
        }),
        ('Пояснение к вопросу', {
            'fields': ('explanation',),
            'classes': ('collapse',),   # свернут по умолчанию
        }),
    )
    formfield_overrides = {
        # делаем текст вопроса компактнее
        models.TextField: {'widget': TextInput(attrs={'size': '80'})},
    }
    show_change_link = True  # если в табличном ряду кликнуть — откроется полный редактирование вопроса

@admin.register(Quiz)
class QuizAdmin(nested_admin.NestedModelAdmin):
    list_display = ('title', 'topic', 'level', 'question_count')
    inlines = [QuestionInline]
    save_on_top = True           # кнопки сохранить/отменить также сверху
    ordering = ('-id',)


##############################
# Question Admin
##############################
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "quiz", "order", "short_text")
    list_filter = ("quiz",)
    search_fields = ("text", "explanation")
    ordering = ("quiz", "order")
    inlines = [ChoiceInline]

    def short_text(self, obj: Question) -> str:
        return obj.text[:50] + ("…" if len(obj.text) > 50 else "")
    short_text.short_description = "Текст вопроса"


##############################
# Choice Admin
##############################
@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "order", "text", "is_correct")
    list_filter = ("question__quiz", "is_correct")
    search_fields = ("text",)
    ordering = ("question", "order")


##############################
# UserQuizAnswer Inline for Session
##############################
class UserQuizAnswerInline(admin.TabularInline):
    model = UserQuizAnswer
    fields = ("question", "choice", "answered_at")
    readonly_fields = ("question", "choice", "answered_at")
    extra = 0
    can_delete = False
    show_change_link = False


##############################
# UserQuizSession Admin
##############################
@admin.register(UserQuizSession)
class UserQuizSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "quiz", "started_at", "finished_at", "score")
    list_filter = ("quiz", "started_at", "finished_at")
    search_fields = ("user__username", "user__chat_id", "quiz__title")
    readonly_fields = ("started_at", "finished_at", "score")
    inlines = [UserQuizAnswerInline]

    def score(self, obj: UserQuizSession) -> int:
        return obj.score()
    score.short_description = "Правильных ответов"


##############################
# UserQuizAnswer Admin
##############################
@admin.register(UserQuizAnswer)
class UserQuizAnswerAdmin(admin.ModelAdmin):
    list_display = ("session", "question", "choice", "answered_at")
    list_filter = ("session__quiz", "answered_at")
    search_fields = ("session__user__username", "question__text", "choice__text")
