# tgbot/admin/quiz.py
import nested_admin
from django.contrib import admin
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
    fields = ('text', 'is_correct', 'order')

class QuestionInline(nested_admin.NestedStackedInline):
    model = Question
    extra = 1
    inlines = [ChoiceInline]
    sortable_field_name = 'order'
    fields = ('text', 'explanation', 'order')
    # если хотите показывать сразу кол-во вариантов:
    readonly_fields = ()

@admin.register(Quiz)
class QuizAdmin(nested_admin.NestedModelAdmin):
    list_display = ('title', 'topic', 'level', 'question_count')
    list_filter = ('topic', 'level')
    search_fields = ('title',)
    inlines = [QuestionInline]


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
