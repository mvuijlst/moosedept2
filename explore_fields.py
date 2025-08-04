#!/usr/bin/env python3
import requests
import json
from urllib.parse import urljoin

API_URL = 'http://127.0.0.1:8000/api/v2/'
PAGES_ENDPOINT = urljoin(API_URL, 'pages/')

# Get news index
response = requests.get(PAGES_ENDPOINT, params={'type': 'nieuws.Index', 'fields': 'id,title'})
index_id = response.json()['items'][0]['id']

# Get just a few fields we know work
url = f'{PAGES_ENDPOINT}?type=nieuws.NewsPage&child_of={index_id}&fields=date,title'
print(f"Requesting: {url}")
response = requests.get(url)
news_pages = response.json()['items']

print(f'\nFound {len(news_pages)} total news pages with date field')

# Also try getting one full page to see all available fields
if news_pages:
    first_page_id = news_pages[0]['id']
    detail_url = f"{PAGES_ENDPOINT}{first_page_id}/"
    print(f"\nGetting full details for first page: {detail_url}")
    detail_response = requests.get(detail_url)
    if detail_response.status_code == 200:
        detail_data = detail_response.json()
        print("Available fields:")
        for key in sorted(detail_data.keys()):
            if key != 'body':  # Skip body as it's long
                print(f"  {key}: {detail_data[key]}")
    else:
        print(f"Error getting details: {detail_response.status_code}")

# Sort by date and show all
def parse_date(date_str):
    if not date_str:
        return datetime.min
    try:
        from datetime import datetime
        return datetime.fromisoformat(date_str)
    except:
        return datetime.min

news_pages_sorted = sorted(news_pages, key=lambda x: parse_date(x.get('date', '')), reverse=True)

print(f'\nAll {len(news_pages_sorted)} pages sorted by date:')
for i, page in enumerate(news_pages_sorted):
    date_field = page.get('date', 'NO DATE')
    print(f'{i+1:2d}. {page["title"]} - {date_field}')
