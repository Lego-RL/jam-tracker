### for functionality related to Spotify

import traceback

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from main import SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET

client: spotipy.Spotify = spotipy.Spotify(
    client_credentials_manager=SpotifyClientCredentials(
        client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET
    )
)


def get_artist_image_url(artist: str) -> str:
    """
    Returns the artist's image URL, retrieved from Spotify.
    """
    try:
        search_info: dict = client.search(q=f"artist:{artist}", limit=1, type="artist")
        artist_info: dict = search_info["artists"]["items"][0]

        return artist_info["images"][0]["url"]

    except Exception:
        traceback.print_exc()
        return None


def get_track_image_url(track: str, artist: str) -> str:
    """
    Returns the track's image URL, retrieved from Spotify.
    """

    try:
        if artist:
            query: str = f"track:{track} artist:{artist}"

        else:
            query: str = f"track:{track}"

        search_info: dict = client.search(q=query, limit=1, type="track")
        track_info: dict = search_info["tracks"]["items"][0]

        return track_info["album"]["images"][0]["url"]

    except Exception:
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print(get_track_image_url("Hot Tea", "half alive"))
