from django.contrib import admin

from .models import Question, QuestionSource


class QuestionSourceInline(admin.TabularInline):
    model = QuestionSource
    extra = 0
    fields = ("passage_number", "manual_name", "revision", "page_number", "score")
    readonly_fields = fields


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "machine", "short_text", "answered", "created_at")
    list_filter = ("answered", "machine")
    search_fields = ("text", "answer", "user__username")
    inlines = [QuestionSourceInline]

    @admin.display(description="Question")
    def short_text(self, obj):
        return obj.text[:60]


@admin.register(QuestionSource)
class QuestionSourceAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "manual_name", "revision", "page_number", "score")
    search_fields = ("manual_name", "text")
