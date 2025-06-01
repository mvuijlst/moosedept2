#!/usr/bin/env python3
import os
import json
import html2text
import requests
import yaml
from datetime import datetime
from urllib.parse import urljoin

# Configuration
API_URL = "http://127.0.0.1:8000/api/v2/"
PAGES_ENDPOINT = urljoin(API_URL, "pages/")
OUTPUT_DIR = "C:\\dev\\hugo\\moosedept\\content\\nieuws"
HTML_CONVERTER = html2text.HTML2Text()
HTML_CONVERTER.ignore_links = False
HTML_CONVERTER.ignore_images = False
HTML_CONVERTER.body_width = 0  # Don't wrap lines

def ensure_dir_exists(directory):
    """Make sure the output directory exists."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")

def get_news_index():
    """Find the news index page."""
    response = requests.get(
        PAGES_ENDPOINT, 
        params={"type": "nieuws.Index", "fields": "id,title"}
    )
    response.raise_for_status()
    data = response.json()
    
    if not data.get('items'):
        raise ValueError("No news index found!")
    
    return data['items'][0]['id']

def get_all_news_pages(index_id):
    """Get all news pages from the API."""
    all_pages = []
    # Use the correct format for requesting fields in Wagtail API
    next_url = f"{PAGES_ENDPOINT}?type=nieuws.NewsPage&child_of={index_id}&fields=date,body,tags"
    
    while next_url:
        print(f"Requesting: {next_url}")
        response = requests.get(next_url)
        
        if response.status_code != 200:
            print(f"API Error: {response.status_code}")
            print(f"Response: {response.text}")
            response.raise_for_status()
            
        data = response.json()
        all_pages.extend(data['items'])
        next_url = data.get('next')
        
        if next_url:
            print(f"Fetched {len(all_pages)} pages, getting more...")
    
    return all_pages

def html_to_markdown(html):
    """Convert HTML to Markdown."""
    if not html:
        return ""
    return HTML_CONVERTER.handle(html)

def create_markdown_file(news_page):
    """Convert a news page to Markdown and save it."""
    title = news_page['title']
    slug = news_page['meta']['slug']
    
    # Handle missing fields
    date_str = news_page.get('date', datetime.now().isoformat())
    body_html = news_page.get('body', '')
    
    # Handle tags - might be missing or null
    tags = []
    if 'tags' in news_page and news_page['tags']:
        tags = news_page['tags']
    
    # Convert body HTML to Markdown
    body_md = html_to_markdown(body_html)
    
    # Create frontmatter
    frontmatter = {
        'title': title,
        'date': date_str,
        'draft': False,
    }
    
    if tags:
        frontmatter['tags'] = tags
    
    # Format as YAML with markdown content
    content = "---\n"
    content += yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)
    content += "---\n\n"
    content += body_md
    
    # Save to file
    filename = os.path.join(OUTPUT_DIR, f"{slug}.md")
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(content)
        
    print(f"Created: {filename}")
    return filename

def main():
    """Main function."""
    print("Starting export of Wagtail news to Hugo Markdown...")
    ensure_dir_exists(OUTPUT_DIR)
    
    try:
        index_id = get_news_index()
        print(f"Found news index with ID: {index_id}")
        
        news_pages = get_all_news_pages(index_id)
        print(f"Found {len(news_pages)} news pages")
        
        for page in news_pages:
            create_markdown_file(page)
            
        print(f"Export complete! {len(news_pages)} files created in {OUTPUT_DIR}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
