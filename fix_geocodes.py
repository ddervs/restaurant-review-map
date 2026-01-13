from geopy.geocoders import Photon
import sqlite3
import time
import re

# Connect to the database
conn = sqlite3.connect('reviews.db')
c = conn.cursor()

# UK postcode pattern - covers all valid formats:
# A9 9AA, A99 9AA, A9A 9AA, AA9 9AA, AA99 9AA, AA9A 9AA
uk_postcode_pattern = re.compile(
    r'^[A-Z]{1,2}[0-9][0-9A-Z]?\s?[0-9][A-Z]{2}$',
    re.IGNORECASE
)

# Find reviews without proper UK postcodes
c.execute("SELECT id, title, postcode FROM reviews WHERE postcode IS NOT NULL")
rows = c.fetchall()

bad_geocodes = []
for row in rows:
    id, title, postcode = row
    if not uk_postcode_pattern.match(postcode.strip()):
        bad_geocodes.append((id, title, postcode))

print(f"Found {len(bad_geocodes)} reviews to re-geocode")

# Initialize Photon geocoder
geolocator = Photon(user_agent="restaurant-review-map", timeout=10)

# Re-geocode with rate limiting
success = 0
failed = 0

for i, (id, title, postcode) in enumerate(bad_geocodes):
    try:
        # Use the postcode field (which contains restaurant name + location) with UK suffix
        query = postcode + ", UK"
        location = geolocator.geocode(query)

        if location:
            c.execute("UPDATE reviews SET location_long=?, location_lat=? WHERE id=?",
                     (location.longitude, location.latitude, id))
            conn.commit()
            success += 1
            print(f"[{i+1}/{len(bad_geocodes)}] ✓ {postcode[:50]} -> ({location.latitude:.4f}, {location.longitude:.4f})")
        else:
            failed += 1
            print(f"[{i+1}/{len(bad_geocodes)}] ✗ {postcode[:50]} -> No result")
    except Exception as e:
        failed += 1
        print(f"[{i+1}/{len(bad_geocodes)}] ✗ {postcode[:50]} -> Error: {e}")

    # Rate limit: 1 request per second
    time.sleep(1)

print(f"\nDone! Success: {success}, Failed: {failed}")

conn.close()
