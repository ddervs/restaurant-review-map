import requests
import sqlite3
import os, time
from datetime import datetime, timedelta
from copy import deepcopy

# Connect to the database
conn = sqlite3.connect('reviews.db')
api_key = os.environ.get('GUARDIAN_API_KEY')

# Get the column names in the reviews table
c = conn.cursor()
c.execute('PRAGMA table_info(reviews)')
columns = [column[1] for column in c.fetchall()]

# Create a table to store the reviews if it doesn't already exist
if not columns:
    conn.execute('''CREATE TABLE reviews
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 date TEXT,
                 title TEXT,
                 text TEXT,
                 url TEXT,
                 author TEXT);''')


# Get the date of the most recent review in the database
c.execute('SELECT MAX(date) FROM reviews')
max_date = c.fetchone()[0]

# If there are no reviews in the database, start from five years  ago
if max_date is None:
    max_date = datetime.now() - timedelta(days=5*365)
else:
# Convert max_date to ISO format for use in API request
    date_format = "%Y-%m-%dT%H:%M:%SZ"
    max_date = datetime.strptime(max_date, date_format) + timedelta(days=1)

max_date_str = max_date.isoformat()

print(f"Most recent date found in database: {max_date_str}")

# Define the API endpoint and parameters
url = "https://content.guardianapis.com/search"
params = {
    "q": "(\"Jay Rayner\" OR \"Grace Dent\")",
    "tags": "contributor,tone/reviews",
    "section": "food",
    "show-fields": "bodyText,byline",
    "api-key": api_key,
    "from-date": max_date_str,
    "page-size": 100,
    "format": "json"
}

# Send requests to the API and get all pages of results
responses = []
page = 1
while True:
    params["page"] = page
    print(params)
    time.sleep(1)
    response = requests.get(url, params=params, headers={'accept': 'application/json'}, allow_redirects=False)
    
    data = response.json()

    responses.append(deepcopy(data))
    # Check if there are more pages of results
    if page * data["response"]["pageSize"] >= data["response"]["total"]:
        break

    # Increment the page number
    page += 1


for data in responses:
        # # Loop through the articles on this page and store the relevant data in the database
    for article in data["response"]["results"]:
        date = article["webPublicationDate"]
        title = article["webTitle"]
        text = article["fields"]["bodyText"]
        url = article["webUrl"]
        try:
            author = article["fields"]["byline"]
        except KeyError:
            author = None

        print(date, title)
        conn.execute(f'INSERT INTO reviews (date, title, text, url, author) VALUES (?, ?, ?, ?, ?)', (date, title, text, url, author))
        conn.commit()


# Close the database connection
conn.close()