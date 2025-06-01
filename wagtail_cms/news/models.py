from django.db import models

from modelcluster.fields import ParentalKey
from modelcluster.contrib.taggit import ClusterTaggableManager
from taggit.models import TaggedItemBase

from wagtail.models import Page
from wagtail.fields import StreamField, RichTextField
from wagtail.admin.panels import FieldPanel
from wagtail.api import APIField
from wagtail.search import index
from wagtail import blocks
from wagtail.blocks import RichTextBlock, TextBlock  # Added TextBlock
from wagtail.images.blocks import ImageChooserBlock

class NewsIndexPage(Page):
    """
    The main news landing page that lists all news articles
    """
    intro = RichTextField(blank=True)
    
    content_panels = Page.content_panels + [
        FieldPanel('intro')
    ]
    
    # Can only have NewsPage children
    subpage_types = ['news.NewsPage']
    
    def get_context(self, request):
        context = super().get_context(request)
        news_items = NewsPage.objects.child_of(self).live().order_by('-date')
        context['news_items'] = news_items
        return context


class NewsPageTag(TaggedItemBase):
    """
    Bridge table for tags on news pages
    """
    content_object = ParentalKey(
        'NewsPage',
        related_name='tagged_items',
        on_delete=models.CASCADE
    )


class NewsPage(Page):
    """
    A single news article
    """
    date = models.DateTimeField("Publicatiedatum")
    tags = ClusterTaggableManager(through=NewsPageTag, blank=True)
    
    body = StreamField([
        ('heading', blocks.CharBlock(form_classname="title")),
        ('paragraph', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),
        ('quote', blocks.BlockQuoteBlock()),
        ('code', blocks.TextBlock(classname="monospace")),  # Changed to TextBlock
    ], use_json_field=True)
    
    search_fields = Page.search_fields + [
        index.SearchField('body'),
        index.RelatedFields('tags', [
            index.SearchField('name'),
        ]),
    ]
    
    content_panels = Page.content_panels + [
        FieldPanel('date'),
        FieldPanel('body'),
        FieldPanel('tags'),
    ]
    
    # Add fields to API
    api_fields = [
        APIField('date'),
        APIField('body'),
        APIField('tags'),
    ]
    
    # Display date in admin list view
    list_display = ['title', 'date', 'latest_revision_created_at']
    
    # Override the display title in admin
    def admin_display_title(self):
        return f"{self.title} ({self.date.strftime('%d-%m-%Y %H:%M')})"
    
    # Can only be created under a NewsIndexPage
    parent_page_types = ['news.NewsIndexPage']

    # Default ordering for the admin interface
    class Meta:
        ordering = ['-date']
        verbose_name = "Nieuwsbericht"
        verbose_name_plural = "Nieuwsberichten"
