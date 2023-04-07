import os
import sqlite3
import requests
from datetime import datetime, timedelta

# Set up Guardian API credentials
api_key = os.environ.get('GUARDIAN_API_KEY')
base_url = 'https://content.guardianapis.com/search'
tags = 'contributor'
q = 'Jay Rayner OR Grace Dent'

# Connect to the SQLite database
conn = sqlite3.connect('reviews.db')
c = conn.cursor()

# Get the date of the most recent review in the database
c.execute('SELECT MAX(date) FROM reviews')
max_date = c.fetchone()[0]

# If there are no reviews in the database, start from five years  ago
if max_date is None:
    max_date = datetime.now() - timedelta(days=5*365)

# Convert max_date to ISO format for use in API request
max_date_str = max_date.date().isoformat()

# Set up API parameters
params = {
    'api-key': api_key,
    'tags': tags,
    'q': q,
    'from-date': max_date_str,
    "show-fields": "bodyText"

}

# Make API request
response = requests.get(base_url, params=params)

# Parse the response JSON and extract review data
reviews = []

print(api_key)
print(response.json())

for result in response.json()['response']['results']:
    review_date = datetime.strptime(result['webPublicationDate'], '%Y-%m-%dT%H:%M:%SZ')
    title = result['webTitle']
    location = result['fields']['bodyText']
    url = result['webUrl']
    reviews.append((title, location, review_date, url))

# Insert new reviews into the database
c.executemany('INSERT INTO reviews VALUES (?, ?, ?, ?, NULL, NULL)', reviews)
conn.commit()

# Close the database connection
conn.close()
