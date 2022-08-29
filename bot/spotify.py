### for functionality related to Spotify

import traceback

import urllib3
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from main import SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET

# client: spotipy.Spotify = spotipy.Spotify(
#     client_credentials_manager=SpotifyClientCredentials(
#         client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET
#     ),
#     requests_timeout=10,
#     retries=10,
# )


def get_artist_image_url(artist: str) -> str:
    """
    Returns the artist's image URL, retrieved from Spotify.
    """
    client: spotipy.Spotify = spotipy.Spotify(
        client_credentials_manager=SpotifyClientCredentials(
            client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET
        ),
        requests_timeout=10,
        retries=10,
    )

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

    client: spotipy.Spotify = spotipy.Spotify(
        client_credentials_manager=SpotifyClientCredentials(
            client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET
        ),
        requests_timeout=10,
        retries=10,
    )

    try:
        if artist:
            query: str = f"track:{track} artist:{artist}"

        else:
            query: str = f"track:{track}"

        try:
            search_info: dict = client.search(q=query, limit=1, type="track")

        except urllib3.exceptions.HTTPError:

            # sometimes urllib3 errors for no reason, best solution was to try once more?
            search_info: dict = client.search(q=query, limit=1, type="track")

        track_info: dict = search_info["tracks"]["items"][0]

        return track_info["album"]["images"][0]["url"]

    except Exception:
        traceback.print_exc()
        return None


def get_album_image_url(album: str, artist: str) -> str:
    """
    Returns the track's image URL, retrieved from Spotify.
    """

    client: spotipy.Spotify = spotipy.Spotify(
        client_credentials_manager=SpotifyClientCredentials(
            client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET
        ),
        requests_timeout=10,
        retries=10,
    )

    # spotify doesn't return pic for this album for some reason
    if album == "Dawn FM (Alternate World)":
        album = "Dawn FM"

    try:
        if artist:
            query: str = f"album:{album} artist:{artist}"

        else:
            query: str = f"album:{album}"

        try:
            search_info: dict = client.search(q=query, limit=1, type="album")

        except urllib3.exceptions.HTTPError:

            # sometimes urllib3 errors for no reason, best solution was to try once more?
            search_info: dict = client.search(q=query, limit=1, type="album")

        try:
            album_info: dict = search_info["albums"]["items"][0]

        except:
            var = search_info["albums"]["items"]
            print(f"{var=}")
            return

        return album_info["images"][0]["url"]

    except Exception:
        traceback.print_exc()
        return None


def get_track_info(track: str, artist: str = None) -> tuple:
    """
    Returns the track's title, album, and cover art url retrieved
    from Spotify.
    """

    client: spotipy.Spotify = spotipy.Spotify(
        client_credentials_manager=SpotifyClientCredentials(
            client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET
        ),
        requests_timeout=10,
        retries=10,
    )

    try:
        if artist:
            query: str = f"track:{track} artist:{artist}"

        else:
            query: str = f"track:{track}"

        search_info: dict = client.search(q=query, limit=1, type="track")
        track_dict = search_info["tracks"]["items"][0]
        track_title: str = track_dict["name"]
        track_album: str = track_dict["album"]["name"]
        track_image_url = track_dict["album"]["images"][0]["url"]

        return (track_title, track_album, track_image_url)

    except IndexError:
        return None

    except Exception:
        traceback.print_exc()
        return None


if __name__ == "__main__":
    pass
    # print(get_track_info("the tradition", "halsey"))
    print(get_album_image_url("Dawn FM (Alternate World)", "The Weeknd"))
