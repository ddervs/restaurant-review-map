from geopy.geocoders import GoogleV3
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
geolocator = GoogleV3(api_key=os.environ.get('GOOGLE_MAPS_API_KEY'))




for row in c.execute("SELECT * FROM reviews WHERE postcode IS NOT NULL"):
    postcode = row[6]
    print(postcode)
    location = geolocator.geocode(postcode)
    if location is not None:
        print(location, location.longitude, location.latitude)
    # if location is not None:
        _c.execute("UPDATE reviews SET location_long=?, location_lat=? WHERE id=?", (location.longitude, location.latitude, row[0]))

# Commit the changes and close the connection
conn.commit()
conn.close()
