import folium
import sqlite3

# Connect to the database
conn = sqlite3.connect('reviews.db')
c = conn.cursor()

# Get the reviews data
c.execute('SELECT location_lat, location_long, sentiment, title, url FROM reviews')
reviews = c.fetchall()

# Create a map centered on the first review
center_lat, center_long = reviews[0][0], reviews[0][1]
m = folium.Map(location=[center_lat, center_long], zoom_start=8)

# Add a title to the map
title_html = '''
             <h3 align="center" style="font-size:20px"><b>Restaurant Reviews Map</b></h3><h4 align="center" style="font-size:14px"><b>Please forgive any inaccuracies! <a href="https://github.com/ddervs/restaurant-review-map">code</a></b></h4>
             '''
# title = folium.map.Marker(location=[center_lat, center_long], icon=None, popup=folium.Popup(html=title_html, max_width=2650))
# title.add_to(m)

m.get_root().html.add_child(folium.Element(title_html))


# Define a color function based on sentiment value
def get_color(sentiment):
    if sentiment < 0:
        return 'red'
    elif sentiment < 0.2:
        return 'lightgreen'
    else:
        return 'green'

# Add markers for each review
for review in reviews:
    lat, lon, sentiment, title, url = review
    color = get_color(sentiment)
    popup_html = f'<a href="{url}">{title}</a>'
    marker = folium.Marker(location=[lat, lon], icon=folium.Icon(color=color), popup=folium.Popup(html=popup_html, max_width=2650))
    marker.add_to(m)

# Save the map as an HTML file
m.save('index.html')
