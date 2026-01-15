import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime

# Connect to the database
conn = sqlite3.connect('reviews.db')
c = conn.cursor()

def is_review(title):
    """Check if title indicates a restaurant review"""
    title_lower = title.lower()
    return 'review' in title_lower or 'visits' in title_lower

# Fetch FT RSS feed
print("Fetching FT RSS feed...")
url = "https://www.ft.com/jay-rayner?format=rss"
resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
root = ET.fromstring(resp.content)

# Get existing URLs
c.execute("SELECT url FROM reviews WHERE url LIKE '%ft.com%'")
existing_urls = {row[0] for row in c.fetchall()}
print(f"Existing FT reviews in DB: {len(existing_urls)}")

# Process RSS items
added = 0
for item in root.findall('.//item'):
    title = item.find('title').text
    link = item.find('link').text
    pub_date = item.find('pubDate').text

    # Skip if not a review
    if not is_review(title):
        continue

    # Skip if already in database
    if link in existing_urls:
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
    added += 1

conn.commit()
conn.close()

print(f"\nDone: {added} new FT reviews added")
