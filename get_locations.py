from geopy.geocoders import Bing
from geopy.point import Point
import sqlite3
import os

# Connect to the database
conn = sqlite3.connect('reviews.db')
c = conn.cursor()
_c = conn.cursor()

# Create a new column for location_long if it doesn't exist
c.execute("PRAGMA table_info(reviews)")
columns = [column[1] for column in c.fetchall()]
if 'location_long' not in columns:
    c.execute("ALTER TABLE reviews ADD COLUMN location_long REAL")

# Create a new column for location_lat if it doesn't exist
if 'location_lat' not in columns:
    c.execute("ALTER TABLE reviews ADD COLUMN location_lat REAL")

# Geocode each address and add the location_long and location_lat values to the database
geolocator = Bing(api_key=os.environ.get('BING_MAPS_API_KEY'))

for row in c.execute("SELECT * FROM reviews WHERE postcode IS NOT NULL AND (location_lat IS NULL OR location_long IS NULL)"):
    postcode = row[6]
    if row[7] is None or row[8] is None:  # check if location_lat or location_long is None
        location = geolocator.geocode(postcode, user_location=Point(latitude=51.5073219, longitude=-0.1276473))
        if location is not None:
            _c.execute("UPDATE reviews SET location_long=?, location_lat=? WHERE id=?", (location.longitude, location.latitude, row[0]))

# Delete any rows with Null latitude or longitude
c.execute("DELETE FROM reviews WHERE location_lat IS NULL OR location_long IS NULL")

# Commit the changes and close the connection
conn.commit()
conn.close()
