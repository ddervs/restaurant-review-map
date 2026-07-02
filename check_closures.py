import sqlite3
import requests
import os
import time
from datetime import datetime, timedelta

# Google Maps Platform terms only permit caching most Places fields for up to
# 30 days, so every restaurant must be re-checked at least that often.
RECHECK_DAYS = 30
COMMIT_EVERY = 25

# Connect to the database
conn = sqlite3.connect('reviews.db')
c = conn.cursor()

# Google Maps API key (Places-enabled; falls back to the legacy shared key)
KEY_NAMES = ('GOOGLE_MAPS_API_KEY_PLACES', 'GOOGLE_MAPS_API_KEY')


def load_api_key():
    for name in KEY_NAMES:
        if os.environ.get(name):
            return os.environ[name]
    try:
        with open('.env') as f:
            for line in f:
                name, _, value = line.strip().partition('=')
                if name in KEY_NAMES and value:
                    return value
    except FileNotFoundError:
        pass
    return None


api_key = load_api_key()
if not api_key:
    print("ERROR: GOOGLE_MAPS_API_KEY_PLACES not found")
    exit(1)

# Add closure columns if they don't exist
c.execute("PRAGMA table_info(reviews)")
columns = [column[1] for column in c.fetchall()]
if 'closed' not in columns:
    c.execute("ALTER TABLE reviews ADD COLUMN closed INTEGER DEFAULT 0")
if 'closed_date' not in columns:
    c.execute("ALTER TABLE reviews ADD COLUMN closed_date TEXT")
if 'closure_checked_at' not in columns:
    c.execute("ALTER TABLE reviews ADD COLUMN closure_checked_at TEXT")
conn.commit()


def find_place_status(name, lat, lng):
    """Look up a place's business_status via the Places Find Place API.

    Returns the status string, or None if the place could not be found.
    Raises for quota/auth errors so the run stops instead of burning quota.
    """
    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "input": name,
        "inputtype": "textquery",
        "fields": "business_status",
        "locationbias": f"point:{lat},{lng}",
        "key": api_key,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    status = data.get("status")

    if status in ("OVER_QUERY_LIMIT", "REQUEST_DENIED"):
        raise RuntimeError(f"Places API error: {status} - {data.get('error_message', '')}")
    if status == "OK" and data.get("candidates"):
        return data["candidates"][0].get("business_status")
    return None


# Check restaurants that have never been checked, or whose last check is
# older than the permitted cache window. Progress is committed as we go, so
# a failed run resumes where it left off.
cutoff = (datetime.now() - timedelta(days=RECHECK_DAYS)).isoformat()
rows = c.execute(
    "SELECT id, title, location_lat, location_long, closed FROM reviews "
    "WHERE location_lat IS NOT NULL AND location_long IS NOT NULL "
    "AND (closure_checked_at IS NULL OR closure_checked_at < ?) "
    "ORDER BY closure_checked_at IS NOT NULL, closure_checked_at",
    (cutoff,),
).fetchall()

if not rows:
    print("All closure statuses are fresh (checked within "
          f"{RECHECK_DAYS} days). Nothing to do.")
    conn.close()
    exit(0)

print(f"Checking closure status for {len(rows)} restaurants...")

newly_closed = 0
not_found = 0
for i, (review_id, title, lat, lng, was_closed) in enumerate(rows, 1):
    try:
        status = find_place_status(title, lat, lng)
    except requests.RequestException as e:
        # Transient network problem: skip this row (it stays due for
        # checking) and carry on.
        print(f"Request failed for '{title}': {e}")
        continue

    now = datetime.now().isoformat()
    if status == "CLOSED_PERMANENTLY":
        if not was_closed:
            c.execute(
                "UPDATE reviews SET closed = 1, closed_date = ?, closure_checked_at = ? WHERE id = ?",
                (now[:10], now, review_id),
            )
            newly_closed += 1
            print(f"CLOSED: {title}")
        else:
            c.execute("UPDATE reviews SET closure_checked_at = ? WHERE id = ?", (now, review_id))
    elif status is not None:
        c.execute(
            "UPDATE reviews SET closed = 0, closed_date = NULL, closure_checked_at = ? WHERE id = ?",
            (now, review_id),
        )
    else:
        # Place not found: keep whatever status we had rather than guessing.
        not_found += 1
        c.execute("UPDATE reviews SET closure_checked_at = ? WHERE id = ?", (now, review_id))

    if i % COMMIT_EVERY == 0:
        conn.commit()
    time.sleep(0.1)  # Rate limit

conn.commit()

c.execute("SELECT COUNT(*) FROM reviews WHERE closed = 1")
closed_count = c.fetchone()[0]
print(f"Done. Checked {len(rows)} restaurants ({not_found} not found on Places). "
      f"{newly_closed} newly closed; {closed_count} closed in total.")

conn.close()
