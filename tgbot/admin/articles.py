# tgbot/admin/articles.py

from django.contrib import admin

from tgbot.models import ArticlesSection, ArticlesSubsection, Article


class ArticleInline(admin.TabularInline):
    model = Article
    fields = ("title", "link")
    extra = 1
    show_change_link = True


@admin.register(ArticlesSubsection)
class ArticlesSubsectionAdmin(admin.ModelAdmin):
    list_display = ("title", "section")
    list_filter = ("section",)
    search_fields = ("title",)
    inlines = [ArticleInline]


class ArticlesSubsectionInline(admin.TabularInline):
    model = ArticlesSubsection
    fields = ("title",)
    extra = 1
    show_change_link = True


@admin.register(ArticlesSection)
class ArticlesSectionAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title",)
    inlines = [ArticlesSubsectionInline]


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "subsection", "link")
    list_filter = ("subsection__section", "subsection")
    search_fields = ("title", "link")
