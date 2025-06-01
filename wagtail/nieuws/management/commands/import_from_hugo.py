import os
import re
import glob
import yaml
import markdown
from django.core.management.base import BaseCommand
from django.utils import timezone
from wagtail.models import Page
from nieuws.models import Index, NewsPage, NewsPageTag
from django.utils.text import slugify
from taggit.models import Tag
from datetime import datetime
from django.db import transaction

class Command(BaseCommand):
    help = 'Import Hugo markdown posts from /nieuws to Wagtail NewsPage items'

    def add_arguments(self, parser):
        parser.add_argument('content_dir', type=str, help='Path to Hugo content directory (parent of /nieuws)')

    def handle(self, *args, **options):
        content_dir = options['content_dir']
        nieuws_dir = os.path.join(content_dir, 'nieuws')
        
        if not os.path.exists(nieuws_dir):
            self.stdout.write(self.style.ERROR(f"Directory not found: {nieuws_dir}"))
            return
            
        # Get the index page where we'll add articles
        try:
            index_page = Index.objects.live().first()
            if not index_page:
                self.stdout.write(self.style.ERROR("No news index page found. Create a news index page first."))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error finding news index: {str(e)}"))
            return
            
        # Find all markdown files
        markdown_files = glob.glob(os.path.join(nieuws_dir, '*.md'))
        
        self.stdout.write(self.style.SUCCESS(f"Found {len(markdown_files)} markdown files to process"))
        
        # Process each markdown file
        for md_file in markdown_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Extract frontmatter and markdown content
                frontmatter, md_content = self.parse_markdown(content)
                
                if not frontmatter:
                    self.stdout.write(self.style.WARNING(f"No frontmatter found in {md_file}, skipping"))
                    continue
                
                # Convert to HTML (simple conversion)
                html_content = markdown.markdown(md_content)
                
                # Get file basename for slug if not specified in frontmatter
                basename = os.path.basename(md_file)
                file_slug = os.path.splitext(basename)[0]
                
                # Extract post data
                title = frontmatter.get('title', file_slug)
                
                # First try to get slug directly from frontmatter
                if 'slug' in frontmatter:
                    slug = frontmatter['slug']
                    self.stdout.write(self.style.SUCCESS(f"Using slug from frontmatter: {slug}"))
                # If no slug in frontmatter, get it from the filename (Hugo behavior)
                else:
                    slug = slugify(file_slug)
                    self.stdout.write(self.style.SUCCESS(f"Using slug from filename: {slug}"))
                
                post_date = self.parse_date(frontmatter.get('date', None))
                tags = frontmatter.get('tags', [])
                draft = frontmatter.get('draft', False)
                
                if draft:
                    self.stdout.write(f"Skipping draft post: {title}")
                    continue
                
                # Create the page
                with transaction.atomic():
                    # Check if page with this slug already exists
                    existing_pages = NewsPage.objects.filter(slug=slug)
                    if existing_pages.exists():
                        self.stdout.write(self.style.WARNING(f"Page with slug '{slug}' already exists, skipping: {title}"))
                        continue
                    
                    # Create the page
                    news_page = NewsPage(
                        title=title,
                        slug=slug,
                        date=post_date,
                        body=html_content,
                    )
                    
                    # Add page to the correct location in site tree
                    index_page.add_child(instance=news_page)
                    
                    # Add tags
                    for tag_name in tags:
                        news_page.tags.add(tag_name)
                    
                    # Publish the page
                    revision = news_page.save_revision()
                    revision.publish()
                    
                    self.stdout.write(self.style.SUCCESS(f"Created post: {title}"))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing {md_file}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS("Import completed"))
    
    def parse_markdown(self, content):
        """Extract frontmatter and markdown content from a markdown file."""
        # Look for frontmatter between --- markers
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
        
        if frontmatter_match:
            frontmatter_text = frontmatter_match.group(1)
            markdown_content = frontmatter_match.group(2)
            
            try:
                frontmatter = yaml.safe_load(frontmatter_text)
                return frontmatter, markdown_content
            except yaml.YAMLError:
                return None, content
        
        return None, content
    
    def parse_date(self, date_str):
        """Convert string or datetime to datetime object."""
        if not date_str:
            return timezone.now()
        
        # If we already have a datetime object, return it directly
        if isinstance(date_str, datetime):
            self.stdout.write(self.style.SUCCESS(f"Date is already a datetime object: {date_str}"))
            return date_str
        
        # Remove any surrounding quotes that might be in the YAML
        if isinstance(date_str, str):
            date_str = date_str.strip('"\'')
            
            # Handle common Hugo date format like '2022-11-22T11:36:06+01:00'
            try:
                # Try to parse ISO format
                date_obj = datetime.fromisoformat(date_str)
                self.stdout.write(self.style.SUCCESS(f"Successfully parsed date: {date_str} → {date_obj}"))
                return date_obj
            except (ValueError, TypeError) as e:
                self.stdout.write(self.style.WARNING(f"Failed to parse date '{date_str}' as ISO format: {e}"))
                try:
                    # Fallback to another format if needed
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    return date_obj
                except (ValueError, TypeError):
                    try:
                        # Try another common format
                        date_obj = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
                        return date_obj
                    except (ValueError, TypeError):
                        try:
                            # Just try to parse the date part
                            if 'T' in date_str:
                                date_part = date_str.split('T')[0]
                            else:
                                date_part = date_str
                            date_obj = datetime.strptime(date_part, '%Y-%m-%d')
                            return date_obj
                        except (ValueError, TypeError, IndexError) as e:
                            self.stdout.write(self.style.ERROR(f"All date parsing attempts failed for '{date_str}': {e}"))
                            return timezone.now()
        
        # If we get here with an unknown type, log and return current time
        self.stdout.write(self.style.ERROR(f"Unexpected date type: {type(date_str)}, value: {date_str}"))
        return timezone.now()
