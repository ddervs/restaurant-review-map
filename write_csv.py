import sqlite3
import csv

# Connect to the SQLite database
conn = sqlite3.connect('reviews.db')

# Get the cursor and execute a SELECT query to fetch all rows from the table
cursor = conn.cursor()
cursor.execute("SELECT * FROM reviews")

# Get the column names from the cursor description
columns = [description[0] for description in cursor.description]

# Open a CSV file for writing
with open('reviews.csv', 'w', newline='') as csv_file:
    writer = csv.writer(csv_file)

    # Write the column headers to the CSV file
    writer.writerow(columns)

    # Loop through the rows returned by the SELECT query and write them to the CSV file
    for row in cursor:
        writer.writerow(row)

# Close the database connection
conn.close()
