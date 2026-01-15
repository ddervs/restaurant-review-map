import sqlite3
import nltk
nltk.download('vader_lexicon', quiet=True)
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
c.execute('SELECT * FROM reviews WHERE sentiment IS NULL')

reviews = c.fetchall()

# Compute sentiment scores for each review and update the database
for review in reviews:
    review_id = review[0]
    title = review[2]
    text = review[3]
    url = review[4]

    # For FT reviews (no article text), use title for sentiment
    if 'ft.com' in url or not text:
        content = title
    else:
        content = text

    scores = sia.polarity_scores(content)
    # Convert compound score from [-1, 1] to [0, 1] for consistency
    sentiment = (scores['compound'] + 1) / 2

    c.execute('UPDATE reviews SET sentiment = ? WHERE id = ?', (sentiment, review_id))

# Commit changes to the database
conn.commit()

# Close the database connection
conn.close()
