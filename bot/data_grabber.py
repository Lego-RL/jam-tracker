import pylast
from sqlalchemy import (
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

import os
from platform import system

import schedule
import time

from data_interface import (
    User,
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


def update_all_user_scrobbles() -> None:
    """
    Meant to grab every user's latest listening data.
    Runs every 5 minutes.
    """

    with Session.begin() as session:
        users: list[User] = session.query(User).all()

        for user in users:
            start_time: int = time.time()
            print(f"updating {user.last_fm_user}")

            lfm_user: pylast.User = network.get_user(user.last_fm_user)

            local_scrobbles: int = get_number_user_scrobbles_stored(user.discord_id)
            lfm_scrobbles: int = lfm_user.get_playcount()

            # no new scrobbles to store
            if local_scrobbles >= lfm_scrobbles:
                continue

            # there are new scrobbles to store if reach this point
            last_scrobble_time: int = get_last_stored_timestamp(user.discord_id)

            if last_scrobble_time:
                last_scrobble_time += (
                    1  # avoid grabbing same track this timestamp came from
                )
            else:
                last_scrobble_time = 0

            new_scrobbles: list[pylast.PlayedTrack] = lfm_user.get_recent_tracks(
                None, time_from=last_scrobble_time, stream=False
            )

            print(f"{last_scrobble_time=}")
            if len(new_scrobbles) < 5:
                for scrobble in new_scrobbles:
                    print(
                        f"storing {scrobble.track} @ {scrobble.timestamp} for {user.last_fm_user}"
                    )

            store_scrobbles(user.discord_id, new_scrobbles)

            end_time: int = time.time()
            print(
                f"fetched {len(new_scrobbles)} for user {user.last_fm_user} in {end_time-start_time} seconds"
            )
            # print(
            #     f"fetched scrobbles for user {user.last_fm_user} in {end_time-start_time} seconds"
            # )


schedule.every(1).minutes.do(update_all_user_scrobbles)
# schedule.every(30).seconds.do(update_all_user_scrobbles)

while True:
    schedule.run_pending()
    time.sleep(1)
