import traceback
import discord
import pylast
from sqlalchemy import Column, ForeignKey, Integer, String, create_engine, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

import os
from platform import system
from typing import Generator

db_path = os.path.join("data", "user_scrobble_data.db")

# need a ../ on linux to go up one level before going down to data folder
nav_to_root = "" if "windows" in system().lower() else r"../"

engine = create_engine(url=f"sqlite:///{nav_to_root}{db_path}", future=True)
Base = declarative_base()

Session = sessionmaker(bind=engine)


class User(Base):
    __tablename__ = "user_account"

    id = Column(Integer, primary_key=True)
    discord_id = Column(Integer, nullable=False)
    last_fm_user = Column(String, nullable=False)

    # each user can have many scrobble entries
    scrobble_entries = relationship(
        "Scrobble", back_populates="user", cascade="all, delete, delete-orphan"
    )

    def __repr__(self):
        return f"User(id={self.id!r}, discord_id={self.discord_id!r}, last_fm_user={self.last_fm_user!r})"


class Scrobble(Base):
    __tablename__ = "scrobble"

    id = Column(Integer, primary_key=True)

    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    album = Column(String)
    lfm_url = Column(String)
    unix_timestamp = Column(Integer, nullable=False)

    user_id = Column(Integer, ForeignKey("user_account.id"))

    # each scrobble belongs to one single user
    # user = relationship("User", uselist=False, cascade="all, delete")
    user = relationship("User", uselist=False)

    def __repr__(self):
        # return f"Scrobble({self.id=!r}, {self.title=!r}, {self.artist=!r}, {self.album=!r}, {self.lfm_url=!r}, {self.cover_art_url=!r}, {self.unix_timestamp=!r}, {self.user_id=!r})"
        return f"Scrobble({self.id=!r}, {self.title=!r}, {self.artist=!r}, {self.album=!r}, {self.lfm_url=!r}, {self.unix_timestamp=!r}, {self.user_id=!r})"


Base.metadata.create_all(engine)


def store_user(discord_id: int, lfm_user: str) -> bool:
    """
    Adds user to user_account table and returns
    True if successful, otherwise False if
    user already had their info stored.
    """

    with Session.begin() as session:
        exists = (
            session.query(User.discord_id).filter_by(discord_id=discord_id).first()
            is not None
        )

        if exists:
            return False

        new_user = User(discord_id=discord_id, last_fm_user=lfm_user)
        session.add(new_user)

        return True


def update_user(discord_id: int, lfm_user: str) -> None:
    """
    Updates a user's information when they were already associated
    with an Last.fm account, and now want to switch to another.

    Returning true represents the user was successfully updated. Return
    False if user supplied same last.fm user as one already stored.
    """

    with Session.begin() as session:
        current_user_obj: User = (
            session.query(User).filter_by(discord_id=discord_id).first()
        )

        if lfm_user == current_user_obj.last_fm_user:
            return False

        else:
            user_obj: User = (
                session.query(User).filter_by(discord_id=discord_id).first()
            )
            session.delete(user_obj)
            session.expire_all()

        # start new session so SQLA doesn't think I'm overwriting when obj with same user_id as deleted
        # is added to DB
    with Session.begin() as session:
        new_user = User(discord_id=discord_id, last_fm_user=lfm_user)
        session.add(new_user)

        # successfully "updated" (deleted & added new user obj) user
        return True


def store_scrobble(discord_id: int, scrobble: pylast.PlayedTrack) -> bool:
    """
    Returns True if the scrobble is sucesfully added
    to the scrobbles table, False otherwise.
    """

    scrobble_track: pylast.Track = scrobble.track
    artist, title = str(scrobble_track).split(sep=" - ", maxsplit=1)

    new_scrobble = Scrobble(
        title=title,
        artist=artist,
        album=scrobble.album,
        lfm_url=scrobble_track.get_url(),
        unix_timestamp=int(scrobble.timestamp),
    )

    with Session.begin() as session:
        user: User = session.query(User).filter_by(discord_id=discord_id).first()

        if not user:
            return False

        user.scrobble_entries.append(new_scrobble)

    return True


def store_scrobbles(discord_id: int, scrobbles: list[pylast.PlayedTrack]) -> None:

    with Session.begin() as session:
        user: User = session.query(User).filter_by(discord_id=discord_id).first()

        if not user:
            return None

        try:
            for scrobble in scrobbles:
                scrobble_track: pylast.Track = scrobble.track
                artist, title = str(scrobble_track).split(sep=" - ", maxsplit=1)

                new_scrobble = Scrobble(
                    title=title,
                    artist=artist,
                    album=scrobble.album,
                    lfm_url=scrobble_track.get_url(),
                    unix_timestamp=int(scrobble.timestamp),
                )

                user.scrobble_entries.append(new_scrobble)

        # generator may be empty? precaution
        except StopIteration:
            return


def get_last_stored_timestamp(discord_id: int) -> Scrobble:
    """
    Return last Scrobble in the database if available.
    """

    with Session.begin() as session:

        # find User.id for given last fm username (user param)
        user_id_query = (
            session.query(User.id).filter_by(discord_id=discord_id).subquery()
        )

        # find the newest scrobble stored for them
        latest_timestamp: int = (
            session.query(func.max(Scrobble.unix_timestamp))
            .filter_by(user_id=user_id_query.c.id)
            .scalar()
        )

        return latest_timestamp


def get_last_scrobbled_track(user: pylast.User) -> pylast.PlayedTrack:
    """
    Return a user's most recent track, or None.
    """

    track: list[pylast.PlayedTrack] = user.get_recent_tracks(limit=1)

    if track != []:
        return track[0]

    return None


def get_number_user_scrobbles_stored(discord_id: int) -> int:
    """
    Return the number of scrobbles stored for a given user.
    """

    with Session.begin() as session:
        count: int = (
            session.query(User)
            .join(User.scrobble_entries)
            .filter(User.discord_id == discord_id)
            .count()
        )

    return count


def check_recent_track_stored(user: pylast.User, discord_id: int) -> bool:
    """
    Return true if the user's last scrobbled track is
    already stored in the database.
    """

    last_track: pylast.PlayedTrack = get_last_scrobbled_track(user)
    last_stored_timestamp = get_last_stored_timestamp(discord_id)

    if last_track.timestamp == last_stored_timestamp:
        return True

    return False


def update_user_scrobbles(
    network: pylast.LastFMNetwork, user_id: int, lfm_user: str
) -> None:
    """
    Attempt to retrieve most recent scrobbles that have not been
    stored in the database yet. If no scrobbles stored for user,
    try to grab entire history. Otherwise, grab all scrobbles
    since the latest stored scrobble for user.
    """

    def update_helper(user: pylast.User, initial_timestamp: int = 0) -> None:
        """
        General method of retrieving and storing 100 tracks
        at a time, that were scrobbled after initial_timestamp.
        initial_timestamp will = 0 when all tracks need gathered.
        """

        if initial_timestamp:
            unstored_scrobbles: Generator[pylast.PlayedTrack] = user.get_recent_tracks(
                limit=None, time_from=initial_timestamp, stream=True
            )
            # TODO: remove once scrobble grabbing error is fixed
            print(f"storing from time {initial_timestamp}")

        else:
            unstored_scrobbles: Generator[pylast.PlayedTrack] = user.get_recent_tracks(
                limit=None,
                stream=True,
            )

        store_scrobbles(user_id, unstored_scrobbles)

    latest_timestamp: int = get_last_stored_timestamp(user_id)
    user: pylast.User = network.get_user(lfm_user)

    if latest_timestamp:
        # make sure it doesn't grab scrobble this timestamp is referring to
        latest_timestamp += 1

        update_helper(user, latest_timestamp)

    else:  # user has no scrobbles stored in database
        update_helper(user)


def retrieve_lfm_username(discord_id: int) -> str:
    """
    Retrieve's last.fm username associated with discord
    user id.
    """

    with Session.begin() as session:
        user: str = (
            session.query(User.last_fm_user).filter_by(discord_id=discord_id).scalar()
        )

        if user:
            return user

        return None  # user not found


def get_lfm_username(invoker_id: int, user: discord.User) -> str:
    """
    Returns last.fm username of the command invoker if no user
    argument is supplied, otherwise returns last.fm username
    belonging to the discord user given.
    """

    if user:
        return retrieve_lfm_username(user.id)

    else:
        return retrieve_lfm_username(invoker_id)


def get_lfm_username_update_data(
    network: pylast.LastFMNetwork, invoker_id: int, user: discord.User = None
) -> str:
    """
    Handles updating local scrobble data on a user if necessary, and
    returns last_fm username for proper user.
    """

    # update supplied user's data and return lfm username
    if user:
        lfm_user = retrieve_lfm_username(user.id)
        if lfm_user:
            update_user_scrobbles(network, user.id, lfm_user)
        return lfm_user

    # update command invoker's data and return lfm username
    else:
        lfm_user = retrieve_lfm_username(invoker_id)
        if lfm_user:
            update_user_scrobbles(network, invoker_id, lfm_user)

        return lfm_user
