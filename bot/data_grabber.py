import pylast
from sqlalchemy import (
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

import os
from platform import system
import time

import math

import json
from pprint import pprint
import requests
import schedule


from data_interface import (
    User,
    Scrobble,
    get_number_user_scrobbles_stored,
    get_last_stored_timestamp,
    store_scrobbles,
)
from main import LFM_API_KEY, LFM_API_SECRET

db_path = os.path.join("data", "user_scrobble_data.db")

# need a ../ on linux to go up one level before going down to data folder
nav_to_root = "" if "windows" in system().lower() else r"../"

engine = create_engine(url=f"sqlite:///{nav_to_root}{db_path}", future=True)
Base = declarative_base()

Session = sessionmaker(bind=engine)

network = pylast.LastFMNetwork(
    api_key=LFM_API_KEY,
    api_secret=LFM_API_SECRET,
)


def track_to_scrobble(track: dict) -> Scrobble | None:
    """
    Takes a track from last.fm's API
    and returns a Scrobble object.
    """

    try:
        if track["@attr"]["nowplaying"]:
            return None

    # key @attr or nowplaying may not be present when track isn't currently playing
    except KeyError:
        pass
    try:
        title: str = track["name"]

    except TypeError:
        print(f"failed on {track=}")
        exit(0)
    artist: str = track["artist"]["#text"]
    album: str = track["album"]["#text"]
    lfm_url: str = track["url"]
    unix_timestamp: int = int(track["date"]["uts"])

    new_scrobble = Scrobble(
        title=title,
        artist=artist,
        album=album,
        lfm_url=lfm_url,
        unix_timestamp=unix_timestamp,
    )

    return new_scrobble


def retrieve_page(
    lfm_user: str,
    from_timestamp: int = None,
    to_timestamp: int = None,
    page_num: int = 1,
) -> dict:
    """
    Retrieve one json page of tracks from last.fm API.
    Return json in dict form, along with page number.
    """

    base_str: str = f"https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&api_key={LFM_API_KEY}&limit=200&format=json"

    params: list[str] = []
    params.append(f"&user={lfm_user}")
    params.append(f"&page={page_num}")

    if from_timestamp:
        params.append(f"&from={from_timestamp}")

    if to_timestamp:
        params.append(f"&to={from_timestamp}")

    data: dict = requests.get(base_str + "".join(params)).json()

    return data


def is_page_empty(page: dict) -> bool:
    """
    Return True if page has no tracks (is empty),
    False if page has content.
    """

    return page["recenttracks"]["@attr"]["total"] == 0


def get_current_page(page: dict) -> int:
    """
    Return current page of data.
    """

    return int(page["recenttracks"]["@attr"]["page"])


def get_total_pages(page: dict) -> int:
    """
    Return total number of pages of data
    to retrieve from last.fm API.
    """

    return int(page["recenttracks"]["@attr"]["totalPages"])


def get_scrobble_objs_from_page(page: dict) -> None:
    """
    Store all scrobbles returned from one page
    of the last.fm API.
    """

    tracks: list[dict] | dict = page["recenttracks"]["track"]

    # no new tracks on page
    if tracks == []:
        return []

    scrobbles: list[Scrobble] = []

    # if there is only one track "tracks" dict may be single track
    if isinstance(tracks, dict):
        if "artist" in tracks.keys():
            if scrobble := track_to_scrobble(tracks):
                scrobbles.append(scrobble)

    # multiple tracks
    else:
        for track in tracks:
            if scrobble := track_to_scrobble(track):
                scrobbles.append(scrobble)

    return scrobbles


def store_scrobble_objs(lfm_user: str, scrobbles: list[Scrobble]) -> None:
    """
    Stores all Scrobble objects to given user's scrobble list.
    """

    with Session.begin() as session:
        user: User = session.query(User).filter_by(last_fm_user=lfm_user).first()

        user.scrobble_entries.extend(scrobbles)


def update_all_user_scrobbles() -> None:
    """
    Meant to grab every user's latest listening data.
    Runs every 5 minutes.
    """

    with Session.begin() as session:
        users: list[User] = session.query(User).all()

        if len(users) == 0:
            print("no users to update")

        for user in users:
            start_time: int = time.time()
            print(f"updating {user.last_fm_user}")

            local_scrobbles: int = get_number_user_scrobbles_stored(user.discord_id)
            last_scrobble_time: int = get_last_stored_timestamp(user.discord_id)

            # need to store all of user's scrobbles
            if local_scrobbles == 0:
                page: dict = retrieve_page(user.last_fm_user, page_num=1)
                total_pages: int = get_total_pages(page)

                scrobbles: list[Scrobble] = get_scrobble_objs_from_page(page)
                store_scrobble_objs(user.last_fm_user, scrobbles)

                for i in range(2, total_pages + 1):
                    page = retrieve_page(user.last_fm_user, page_num=i)
                    scrobbles: list[Scrobble] = get_scrobble_objs_from_page(page)
                    store_scrobble_objs(user.last_fm_user, scrobbles)

            else:
                page: dict = retrieve_page(
                    user.last_fm_user, from_timestamp=last_scrobble_time + 1, page_num=1
                )
                total_pages: int = get_total_pages(page)

                # no new tracks to store
                if is_page_empty(page):
                    continue

                else:
                    scrobbles: list[Scrobble] = get_scrobble_objs_from_page(page)
                    store_scrobble_objs(user.last_fm_user, scrobbles)

                    for i in range(2, total_pages + 1):
                        print(f"on page {i} of {total_pages}")
                        page = retrieve_page(
                            user.last_fm_user,
                            from_timestamp=last_scrobble_time + 1,
                            page_num=i,
                        )
                        scrobbles: list[Scrobble] = get_scrobble_objs_from_page(page)
                        store_scrobble_objs(user.last_fm_user, scrobbles)

            end_time: int = time.time()
            print(f"stored scrobbles in {end_time-start_time} seconds")


schedule.every(1).minutes.do(update_all_user_scrobbles)

if __name__ == "__main__":

    while True:
        schedule.run_pending()
        time.sleep(1)
