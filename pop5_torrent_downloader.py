import feedparser
import requests
import streamlit as st

# Constants
RSS_FEED_URL = "https://iptorrents.com/t.rss?u=2179648;tp=19d5ac2544e3fad759f5d236d75140dc;pins"

def fetch_and_sort_torrents(rss_url):
    """Fetch the RSS feed and sort torrents by seeders."""
    feed = feedparser.parse(rss_url)
    torrents = []

    for entry in feed.entries:
        title = entry.title
        link = entry.link
        # Parse seeders from the title (example: "[12345 Seeders]")
        try:
            seeders = int(title.split("[")[1].split(" ")[0])
        except (IndexError, ValueError):
            seeders = 0
        torrents.append({"title": title, "link": link, "seeders": seeders})
    
    # Sort torrents by the number of seeders in descending order
    torrents.sort(key=lambda x: x["seeders"], reverse=True)
    return torrents

def download_torrent_file(torrent_url, file_name):
    """Download the torrent file."""
    response = requests.get(torrent_url)
    if response.status_code == 200:
        with open(file_name, "wb") as file:
            file.write(response.content)
        return file_name
    else:
        return None

# Streamlit Web Interface
st.title("Popular Torrents Downloader")
st.write("Fetching the top 5 most popular torrents based on seeders...")

# Fetch and display torrents
torrents = fetch_and_sort_torrents(RSS_FEED_URL)
top_torrents = torrents[:5]

if top_torrents:
    for i, torrent in enumerate(top_torrents, 1):
        st.subheader(f"{i}. {torrent['title']}")
        st.write(f"Seeders: {torrent['seeders']}")
        st.write(f"[Download Torrent File]({torrent['link']})")

        # Optionally download the file
        if st.button(f"Download {i}"):
            file_name = torrent['title'].replace(" ", "_") + ".torrent"
            downloaded_file = download_torrent_file(torrent['link'], file_name)
            if downloaded_file:
                st.success(f"Downloaded: {downloaded_file}")
            else:
                st.error(f"Failed to download: {torrent['title']}")
else:
    st.write("No torrents found.")


