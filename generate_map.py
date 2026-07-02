import folium
from folium.plugins import Search
import sqlite3

# Connect to the database
conn = sqlite3.connect('reviews.db')
c = conn.cursor()

# The closure columns only exist once closure tracking has run, so degrade
# gracefully when they are absent.
c.execute("PRAGMA table_info(reviews)")
columns = [column[1] for column in c.fetchall()]
closed_select = "COALESCE(closed, 0), closed_date" if 'closed' in columns else "0, NULL"
roundup_guard = " AND COALESCE(roundup, 0) = 0" if 'roundup' in columns else ""

# Get the reviews data (exclude rows with NULL coordinates, and round-ups
# that don't describe a single restaurant)
c.execute(f'SELECT location_lat, location_long, sentiment, title, url, author, {closed_select} '
          f'FROM reviews WHERE location_lat IS NOT NULL AND location_long IS NOT NULL{roundup_guard}')
reviews = c.fetchall()

# Create a map centered on Edinburgh
center_lat, center_long = 55.9533, -3.1883
m = folium.Map(location=[center_lat, center_long], zoom_start=8)

# Add a title to the map
title_html = '''
             <h3 align="center" style="font-size:20px"><b>Restaurant Reviews Map</b></h3><h4 align="center" style="font-size:14px"><b>Please forgive any inaccuracies! <a href="https://github.com/ddervs/restaurant-review-map">code</a></b></h4>
             '''
m.get_root().html.add_child(folium.Element(title_html))


# Define a color function based on sentiment value.
# Sentiment is on a [0, 1] scale (0.5 = mixed), so red is a pan, orange is
# mixed and green is a recommendation.
def get_color(sentiment):
    if sentiment < 0.4:
        return 'red'
    elif sentiment < 0.6:
        return 'orange'
    else:
        return 'green'


def get_reviewer(author):
    author = author or ''
    if 'Grace Dent' in author:
        return 'Grace Dent'
    if 'Rayner' in author:
        return 'Jay Rayner'
    return 'Other contributors'


# One toggleable layer per reviewer, so the layer control acts as a filter
reviewer_groups = {}
for reviewer in ('Grace Dent', 'Jay Rayner', 'Other contributors'):
    reviewer_groups[reviewer] = folium.FeatureGroup(name=reviewer, show=True).add_to(m)

# Invisible point layer that only exists to power the search box
search_features = []

# Add markers for each review
for review in reviews:
    lat, lon, sentiment, title, url, author, closed, closed_date = review
    if closed:
        color = 'gray'
        closed_label = f'[CLOSED since {closed_date}]' if closed_date else '[CLOSED]'
        popup_html = f'<a href="{url}"><s>{title}</s> {closed_label}</a>'
    else:
        color = get_color(sentiment)
        popup_html = f'<a href="{url}">{title}</a>'
    marker = folium.Marker(location=[lat, lon], icon=folium.Icon(color=color),
                           popup=folium.Popup(html=popup_html, max_width=2650),
                           tooltip=title)
    marker.add_to(reviewer_groups[get_reviewer(author)])
    search_features.append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {"name": title},
    })

search_index = folium.GeoJson(
    {"type": "FeatureCollection", "features": search_features},
    name="search index",
    control=False,
    marker=folium.CircleMarker(radius=0, weight=0, fill=False),
).add_to(m)

Search(
    layer=search_index,
    search_label='name',
    placeholder='Search restaurants...',
    collapsed=True,
    zoom=16,
).add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

# Save the map as an HTML file
m.save('index.html')
