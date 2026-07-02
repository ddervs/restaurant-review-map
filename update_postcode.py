import csv
import os
import re
import sqlite3

# Connect to the reviews database
conn = sqlite3.connect('reviews.db')

# Create a cursor object
c = conn.cursor()

# Compile the postcode pattern regex
postcode_pattern = re.compile(r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}\b')

# Street addresses like "14 Station Parade" or "22-24 Prospect Street",
# usually found in the address footer of Grace Dent's reviews
STREET_TYPES = (
    'Street|Road|Lane|Avenue|Square|Place|Parade|Row|Hill|Terrace|Walk|'
    'Gardens|Quay|Wharf|Green|Market|Crescent|Drive|Yard|Mews|Broadway|'
    'Promenade|Esplanade|Embankment|Dock|Basin|Grove|Court|Close|Way|End'
)
street_pattern = re.compile(
    rf"\b\d+[a-zA-Z]?(?:\s*[-–&]\s*\d+[a-zA-Z]?)?\s+(?:[A-Z][A-Za-z']*\s+){{0,4}}(?:{STREET_TYPES})\b"
)

# Titles that are round-ups, opinion columns or features rather than a
# review of a single restaurant; these can't be pinned to one location
roundup_pattern = re.compile(
    r'\bbest\b|favourite|runners[ -]?up|places to eat|guide to|'
    r'restaurants of the year|awards',
    re.IGNORECASE,
)

# Check if the postcode column already exists in the reviews table
c.execute("SELECT * FROM pragma_table_info('reviews') WHERE name='postcode'")
postcode_column_exists = bool(c.fetchone())

if not postcode_column_exists:
    # Add a new 'postcode' column to the 'reviews' table
    c.execute('ALTER TABLE reviews ADD COLUMN postcode TEXT')

c.execute("SELECT * FROM pragma_table_info('reviews') WHERE name='roundup'")
if not c.fetchone():
    c.execute('ALTER TABLE reviews ADD COLUMN roundup INTEGER DEFAULT 0')


def load_overrides():
    """Manual postcode/query overrides for known problem cases, keyed by
    review title. See postcode_overrides.csv."""
    overrides = {}
    if os.path.exists('postcode_overrides.csv'):
        with open('postcode_overrides.csv') as f:
            for row in csv.DictReader(f):
                overrides[row['title']] = row['query']
    return overrides


def is_roundup(title, url):
    """Detect round-ups, opinion pieces and features that don't review a
    single restaurant."""
    if roundup_pattern.search(title):
        return True
    # Weekly reviews all carry "review"/"reviews"/"visits" in the title;
    # opinion columns and diary pieces don't
    return not re.search(r'\breviews?\b|\bvisits?\b', title, re.IGNORECASE)


def parse_ft_title(title):
    """Extract restaurant and location from FT review title for geocoding"""
    # Normalize curly/smart quotes to straight equivalents
    title_norm = title.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')

    # Pattern: "Restaurant, Location: description" (no "reviews" keyword)
    colon_match = re.match(r"^['\"]?(.+?),\s+([A-Za-z'\s]+?):\s+", title_norm)
    if colon_match:
        restaurant = colon_match.group(1).strip().strip("'\"")
        location = colon_match.group(2).strip()
        if 0 < len(restaurant) < 50:
            return f"{restaurant} restaurant, {location}"

    word_class = r"[A-Za-z'\s]+"
    patterns = [
        rf'reviews?\s+(?:the\s+)?(.+?)\s+in\s+({word_class})(?:\s*[—–-]|$)',
        rf'reviews?\s+(?:the\s+)?(.+?),\s+({word_class})(?:\s*[—–-]|$)',
        rf'reviews?\s+(?:the\s+)?(.+?)\s+at\s+({word_class})(?:\s*[—–-]|$)',
        rf'visits?\s+(?:the\s+)?(.+?)\s+in\s+({word_class})(?:\s*[—–-]|$)',
    ]

    generic_prefix = re.compile(r'^(a|an)\s', re.IGNORECASE)
    for pattern in patterns:
        match = re.search(pattern, title_norm, re.IGNORECASE)
        if match:
            restaurant = match.group(1).strip()
            location = match.group(2).strip().strip("'\"")
            if 0 < len(restaurant) < 50:
                if generic_prefix.match(restaurant):
                    # Generic name (e.g. "a cult restaurant") — geocode by location only
                    return location
                return f"{restaurant} restaurant, {location}"

    # Fallback: use whole title for geocoding
    return title


def extract_query(title, text, author, url):
    """Work out the best geocoding query for a review.

    Preference order: a full UK postcode anywhere in the text, then a
    street address from the address footer combined with the name and
    town from the title, then the old name-and-town fallback.
    """
    text = text or ''

    if 'ft.com' in url:
        return parse_ft_title(title)

    # A full UK postcode beats everything (Jay Rayner's reviews open with
    # the restaurant's full address)
    postcode_match = postcode_pattern.search(text)
    if postcode_match:
        return postcode_match.group(0)

    # Grace Dent's titles start "Name, Town: ..." and her reviews end with
    # an address footer like "Hawthorn 14 Station Parade, Kew, 020-..."
    name_town = title.split(':')[0].strip()
    footer = text[-1000:]
    street_match = street_pattern.search(footer)
    if street_match:
        name = name_town.split(',')[0].strip()
        # Everything after the name ("Kew" / "Lymington, Hampshire") gives
        # the geocoder enough context to pick the right street
        town = name_town.split(',', 1)[1].strip() if ',' in name_town else ''
        parts = [p for p in (name, street_match.group(0), town) if p]
        return ', '.join(parts) + ', UK'

    if author == 'Grace Dent':
        return name_town

    return None


overrides = load_overrides()

# Only process rows that don't have a postcode yet: older rows have their
# article text stripped from the committed dump (Guardian terms), so they
# can't be re-extracted — and their stored postcode is still valid.
c.execute('SELECT * FROM reviews WHERE postcode IS NULL')

# Loop through each row and extract the postcode
for row in c.fetchall():
    url = row[4]
    title = row[2]
    text = row[3]
    author = row[5]

    if title in overrides:
        postcode = overrides[title]
        roundup = 0
    elif is_roundup(title, url):
        postcode = None
        roundup = 1
    else:
        postcode = extract_query(title, text, author, url)
        roundup = 0

    # Update the 'postcode' column with the extracted postcode
    c.execute('UPDATE reviews SET postcode = ?, roundup = ? WHERE rowid = ?', (postcode, roundup, row[0]))

# Commit the changes to the database
conn.commit()

# Close the database connection
conn.close()
