import sqlite3
import nltk
nltk.download('vader_lexicon')
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Connect to the SQLite database
conn = sqlite3.connect('reviews.db')
c = conn.cursor()

# Check if the sentiment column exists, and create it if it does not
c.execute("PRAGMA table_info(reviews)")
columns = [column[1] for column in c.fetchall()]
if 'sentiment' not in columns:
    c.execute("ALTER TABLE reviews ADD COLUMN sentiment REAL")

# Initialize VADER sentiment analyzer
sia = SentimentIntensityAnalyzer()

# Get all reviews with null sentiment
# c.execute('SELECT * FROM reviews WHERE sentiment IS NULL')
c.execute('SELECT * FROM reviews')

reviews = c.fetchall()

# Compute sentiment scores for each review and update the database
for review in reviews:
    date = review[1]
    text = review[2]
    scores = sia.polarity_scores(text)
    sentiment = scores['compound']
    c.execute('UPDATE reviews SET sentiment = ? WHERE date = ?', (sentiment, date))

# Commit changes to the database
conn.commit()

# Close the database connection
conn.close()
