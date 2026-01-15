import sqlite3
import requests
import os
import re
import time

# Connect to the database
conn = sqlite3.connect('reviews.db')
c = conn.cursor()
_c = conn.cursor()

# Google Maps API key
api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
if not api_key:
    try:
        with open('.env') as f:
            for line in f:
                if line.startswith('GOOGLE_MAPS_API_KEY='):
                    api_key = line.strip().split('=', 1)[1]
                    break
    except FileNotFoundError:
        pass

if not api_key:
    print("ERROR: GOOGLE_MAPS_API_KEY not found")
    exit(1)

# Create location columns if they don't exist
c.execute("PRAGMA table_info(reviews)")
columns = [column[1] for column in c.fetchall()]
if 'location_long' not in columns:
    c.execute("ALTER TABLE reviews ADD COLUMN location_long REAL")
if 'location_lat' not in columns:
    c.execute("ALTER TABLE reviews ADD COLUMN location_lat REAL")

def geocode(query):
    """Geocode using Google Maps API"""
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": query, "key": api_key}
    resp = requests.get(url, params=params)
    data = resp.json()

    if data['status'] == 'OK' and data['results']:
        loc = data['results'][0]['geometry']['location']
        return loc['lat'], loc['lng']
    return None, None

# Geocode reviews with missing coordinates
for row in c.execute("SELECT * FROM reviews WHERE postcode IS NOT NULL AND (location_lat IS NULL OR location_long IS NULL)"):
    review_id = row[0]
    postcode = row[6]

    if row[7] is None or row[8] is None:
        # Add UK suffix for UK postcodes
        if re.match(r'^[A-Z]{1,2}\d', postcode):
            query = postcode + ", UK"
        else:
            query = postcode

        lat, lng = geocode(query)
        time.sleep(0.1)  # Rate limit

        if lat is not None:
            _c.execute("UPDATE reviews SET location_lat=?, location_long=? WHERE id=?", (lat, lng, review_id))
            print(f"Geocoded: {postcode} -> {lat}, {lng}")
        else:
            print(f"Failed to geocode: {postcode}")

# Delete any rows with Null latitude or longitude
c.execute("DELETE FROM reviews WHERE location_lat IS NULL OR location_long IS NULL")

# Commit the changes and close the connection
conn.commit()
conn.close()
