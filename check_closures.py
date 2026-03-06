import sqlite3
import requests
import os
import time
from datetime import datetime, timedelta

RECHECK_DAYS = 90  # Re-check all restaurants every ~quarter

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

# Add closed column if it doesn't exist
c.execute("PRAGMA table_info(reviews)")
columns = [column[1] for column in c.fetchall()]
if 'closed' not in columns:
    c.execute("ALTER TABLE reviews ADD COLUMN closed INTEGER DEFAULT 0")
if 'closed_date' not in columns:
    c.execute("ALTER TABLE reviews ADD COLUMN closed_date TEXT")

# Metadata table to track last closure check date
c.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)")
conn.commit()

# Check if a full recheck is due
c.execute("SELECT value FROM metadata WHERE key = 'last_closure_check'")
row = c.fetchone()
last_check = datetime.fromisoformat(row[0]) if row else None

if last_check and (datetime.now() - last_check) < timedelta(days=RECHECK_DAYS):
    # Check only new restaurants (closed IS NULL)
    c.execute(
        "SELECT COUNT(*) FROM reviews "
        "WHERE location_lat IS NOT NULL AND location_long IS NOT NULL AND closed IS NULL"
    )
    new_count = c.fetchone()[0]
    if new_count == 0:
        print(f"Last full check was {last_check.date()}. Next recheck after {(last_check + timedelta(days=RECHECK_DAYS)).date()}. No new restaurants to check.")
        conn.close()
        exit(0)
    else:
        print(f"Checking {new_count} new restaurants (last full check: {last_check.date()})...")
else:
    # Time for a full recheck — reset all to NULL so they get re-queried
    print("Quarterly recheck: resetting all closure statuses...")
    c.execute("UPDATE reviews SET closed = NULL")
    conn.commit()


def find_place(name, lat, lng):
    """Find a place using Google Places API Text Search and return its business_status."""
    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "input": name,
        "inputtype": "textquery",
        "fields": "business_status",
        "locationbias": f"point:{lat},{lng}",
        "key": api_key,
    }
    resp = requests.get(url, params=params)
    data = resp.json()

    if data.get("status") == "OK" and data.get("candidates"):
        return data["candidates"][0].get("business_status")
    return None


# Check closure status for restaurants that haven't been checked yet
rows = c.execute(
    "SELECT id, title, location_lat, location_long FROM reviews "
    "WHERE location_lat IS NOT NULL AND location_long IS NOT NULL AND closed IS NULL"
).fetchall()

print(f"Checking closure status for {len(rows)} restaurants...")

for row in rows:
    review_id, title, lat, lng = row
    status = find_place(title, lat, lng)
    time.sleep(0.1)  # Rate limit

    if status == "CLOSED_PERMANENTLY":
        _c.execute("UPDATE reviews SET closed = 1 WHERE id = ?", (review_id,))
        print(f"CLOSED: {title}")
    elif status is not None:
        _c.execute("UPDATE reviews SET closed = 0 WHERE id = ?", (review_id,))
    else:
        # Could not find the place, mark as unchecked (0)
        _c.execute("UPDATE reviews SET closed = 0 WHERE id = ?", (review_id,))
        print(f"Not found: {title}")

conn.commit()

# Update last check timestamp
c.execute(
    "INSERT OR REPLACE INTO metadata (key, value) VALUES ('last_closure_check', ?)",
    (datetime.now().isoformat(),)
)
conn.commit()

# Report results
c.execute("SELECT COUNT(*) FROM reviews WHERE closed = 1")
closed_count = c.fetchone()[0]
print(f"Done. {closed_count} restaurants marked as permanently closed.")

conn.close()
