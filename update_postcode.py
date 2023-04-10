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


# Select all rows from the 'reviews' table
c.execute('SELECT * FROM reviews')

# Loop through each row and extract the postcode
for row in c.fetchall():
    # Check if the author is Grace Dent
    if row[5] == 'Grace Dent':
        # Extract the postcode from the title
        postcode = row[2].split(':')[0].strip()
    else:
        # Extract the postcode from the text
        postcode_match = postcode_pattern.search(row[3])
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
