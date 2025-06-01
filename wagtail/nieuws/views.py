from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from wagtail.models import Page
from .models import Index, NewsPage
from taggit.models import Tag

def tag_index(request, tag):
    """
    View function for displaying news items filtered by tag
    """
    # Find the news index page
    news_index = Index.objects.live().first()
    
    if not news_index:
        # Handle case where news index doesn't exist
        return render(request, '404.html', {}, status=404)
    
    # Find the tag object
    tag_instance = get_object_or_404(Tag, slug=tag)
    
    # Get all news pages filtered by tag
    newspages = NewsPage.objects.live().filter(tags__name=tag_instance.name).order_by('-date')
    
    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(newspages, 50)  # Show 10 news items per page
    try:
        newspages = paginator.page(page)
    except PageNotAnInteger:
        newspages = paginator.page(1)
    except EmptyPage:
        newspages = paginator.page(paginator.num_pages)
    
    return render(request, 'nieuws/index.html', {
        'page': news_index,
        'newspages': newspages,
        'filter_tag': tag_instance.name,
    })

def paginated_index(request, page_number):
    """
    View function for displaying paginated news items
    """
    # Find the news index page
    news_index = Index.objects.live().first()
    
    if not news_index:
        # Handle case where news index doesn't exist
        return render(request, '404.html', {}, status=404)
    
    # Get all news pages
    newspages = NewsPage.objects.live().child_of(news_index).order_by('-date')
    
    # Filter by tag if specified in URL query params
    tag = request.GET.get('tag')
    if tag:
        newspages = newspages.filter(tags__name=tag)
    
    # Pagination
    paginator = Paginator(newspages, 10)  # Show 10 news items per page
    try:
        newspages = paginator.page(page_number)
    except PageNotAnInteger:
        newspages = paginator.page(1)
    except EmptyPage:
        newspages = paginator.page(paginator.num_pages)
    
    return render(request, 'nieuws/index.html', {
        'page': news_index,
        'newspages': newspages,
    })
