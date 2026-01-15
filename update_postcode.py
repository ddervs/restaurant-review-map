import re
import sqlite3

# Connect to the reviews database
conn = sqlite3.connect('reviews.db')

# Create a cursor object
c = conn.cursor()

# Compile the postcode pattern regex
postcode_pattern = re.compile(r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}\b')

# Check if the postcode column already exists in the reviews table
c.execute("SELECT * FROM pragma_table_info('reviews') WHERE name='postcode'")
postcode_column_exists = bool(c.fetchone())

if not postcode_column_exists:
    # Add a new 'postcode' column to the 'reviews' table
    c.execute('ALTER TABLE reviews ADD COLUMN postcode TEXT')


def parse_ft_title(title):
    """Extract restaurant and location from FT review title for geocoding"""
    patterns = [
        r'reviews?\s+(?:the\s+)?(.+?)\s+in\s+([A-Za-z\s]+?)(?:\s*[—–-]|$)',
        r'reviews?\s+(?:the\s+)?(.+?),\s+([A-Za-z\s]+?)(?:\s*[—–-]|$)',
        r'visits?\s+(?:the\s+)?(.+?)\s+in\s+([A-Za-z\s]+?)(?:\s*[—–-]|$)',
    ]

    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            restaurant = match.group(1).strip()
            location = match.group(2).strip()
            # Validate - reject if parsed restaurant looks wrong
            if 5 < len(restaurant) < 50:
                return f"{restaurant} restaurant, {location}"

    # Fallback: use whole title for geocoding
    return title


# Select all rows from the 'reviews' table
c.execute('SELECT * FROM reviews')

# Loop through each row and extract the postcode
for row in c.fetchall():
    url = row[4]
    title = row[2]
    text = row[3]
    author = row[5]

    # Check if FT review (use title for geocoding)
    if 'ft.com' in url:
        postcode = parse_ft_title(title)
    # Check if the author is Grace Dent (postcode in title)
    elif author == 'Grace Dent':
        postcode = title.split(':')[0].strip()
    # Otherwise extract postcode from text (Observer Jay Rayner)
    else:
        postcode_match = postcode_pattern.search(text)
        if postcode_match:
            postcode = postcode_match.group(0)
        else:
            postcode = None

    # Update the 'postcode' column with the extracted postcode
    c.execute('UPDATE reviews SET postcode = ? WHERE rowid = ?', (postcode, row[0]))

# Commit the changes to the database
conn.commit()

# Close the database connection
conn.close()
