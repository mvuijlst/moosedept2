from django.db import models

# Add these:
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.search import index


class Index(Page):
    intro = RichTextField(blank=True)

    def get_context(self, request):
        context = super().get_context(request)
        newspages = self.get_children().live().order_by('-first_published_at')
        context['newspages'] = newspages
        return context

    content_panels = Page.content_panels + ["intro"]

class NewsPage(Page):
    date = models.DateTimeField("Publicatiedatum")
    body = RichTextField(blank=True)

    search_fields = Page.search_fields + [
        index.SearchField('body'),
    ]

    content_panels = Page.content_panels + ["date", "body"]