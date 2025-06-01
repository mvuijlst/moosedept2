from django.db import models
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from taggit.models import Tag

# Add these:
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.search import index
from wagtail.admin.panels import FieldPanel
from modelcluster.fields import ParentalKey
from modelcluster.contrib.taggit import ClusterTaggableManager
from taggit.models import TaggedItemBase


class NewsPageTag(TaggedItemBase):
    content_object = ParentalKey(
        'NewsPage',
        related_name='tagged_items',
        on_delete=models.CASCADE
    )


class Index(Page):
    intro = RichTextField(blank=True)

    def get_context(self, request):
        context = super().get_context(request)
        
        # Get all NewsPage objects that are children of this index, sorted by date
        newspages = NewsPage.objects.live().child_of(self).order_by('-date')
        
        # Filter by tag if specified in URL query params
        tag = request.GET.get('tag')
        if tag:
            newspages = newspages.filter(tags__name=tag)
        
        # Pagination
        page = request.GET.get('page')
        paginator = Paginator(newspages, 50)  # Show 10 news items per page
        try:
            newspages = paginator.page(page)
        except PageNotAnInteger:
            newspages = paginator.page(1)
        except EmptyPage:
            newspages = paginator.page(paginator.num_pages)
            
        context['newspages'] = newspages
        return context
        
    def get_tags(self):
        # Get all NewsPage objects that are descendants of this index page
        news_pages = NewsPage.objects.descendant_of(self).live()
        
        # Get a list of tags with count
        tag_dict = {}
        for page in news_pages:
            for tag in page.tags.all():
                if tag.name in tag_dict:
                    tag_dict[tag.name] += 1
                else:
                    tag_dict[tag.name] = 1
        
        # Convert to list of objects with name and count attributes
        tags = [{'name': name, 'count': count} for name, count in tag_dict.items()]
        tags.sort(key=lambda x: x['name'])
        return tags

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]


class NewsPage(Page):
    date = models.DateTimeField("Publicatiedatum")
    body = RichTextField(blank=True)
    tags = ClusterTaggableManager(through=NewsPageTag, blank=True)

    search_fields = Page.search_fields + [
        index.SearchField('body'),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("date"), 
        FieldPanel("body"),
        FieldPanel("tags"),
    ]