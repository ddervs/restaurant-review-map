CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_name TEXT,
    location TEXT,
    date_reviewed DATE,
    url TEXT,
    sentiment FLOAT,
    reviewer TEXT
);
