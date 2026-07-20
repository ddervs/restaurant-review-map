import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urldefrag, urlsplit, urlunsplit

# Connect to the database
conn = sqlite3.connect('reviews.db')
c = conn.cursor()

def is_review(title):
    """Check if title indicates a restaurant review"""
    title_lower = title.lower()
    return 'review' in title_lower or 'visits' in title_lower

def canonical_url(url):
    """Drop query strings and fragments.

    The FT feed tags links with a per-feed syndication parameter
    (e.g. ?syn-25a6b1a6=1) that changes over time, so the raw link is
    useless for deduplication.
    """
    parts = urlsplit(urldefrag(url).url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))

# Fetch FT RSS feed
print("Fetching FT RSS feed...")
url = "https://www.ft.com/jay-rayner?format=rss"
resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
root = ET.fromstring(resp.content)

# Get existing URLs
c.execute("SELECT url FROM reviews WHERE url LIKE '%ft.com%'")
existing_urls = {canonical_url(row[0]) for row in c.fetchall()}
print(f"Existing FT reviews in DB: {len(existing_urls)}")

# Titles are UNIQUE in the schema, so guard against re-runs where the URL has
# changed but the article has not
c.execute("SELECT title FROM reviews")
existing_titles = {row[0] for row in c.fetchall()}

# Process RSS items
added = 0
for item in root.findall('.//item'):
    title = item.find('title').text
    link = canonical_url(item.find('link').text)
    pub_date = item.find('pubDate').text

    # Skip if not a review
    if not is_review(title):
        continue

    # Skip if already in database
    if link in existing_urls or title in existing_titles:
        continue

    print(f"New review: {title[:60]}...")

    # Parse date
    try:
        dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
        date_str = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except:
        date_str = None

    # Insert into database (postcode, location, sentiment will be filled by other scripts)
    c.execute('''INSERT INTO reviews (date, title, text, url, author)
                 VALUES (?, ?, ?, ?, ?)''',
              (date_str, title, '', link, 'Jay Rayner'))
    existing_urls.add(link)
    existing_titles.add(title)
    added += 1

conn.commit()
conn.close()

print(f"\nDone: {added} new FT reviews added")
