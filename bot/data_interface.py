import discord
import pylast
import sqlalchemy
from sqlalchemy import (
    Column,
    ForeignKey,
    DateTime,
    Integer,
    String,
    create_engine,
    func,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

import os
import time

db_path = os.path.join("data", "user_scrobble_data.db")

engine = create_engine(url=f"sqlite:///{db_path}", future=True)
Base = declarative_base()

Session = sessionmaker(bind=engine)
session: Session = Session()


class User(Base):
    __tablename__ = "user_account"

    id = Column(Integer, primary_key=True)
    discord_id = Column(Integer, nullable=False)
    last_fm_user = Column(String, nullable=False)

    # each user can have many scrobble entries
    scrobble_entries = relationship("Scrobble", back_populates="user")

    def __repr__(self):
        return f"User(id={self.id!r}, discord_id={self.discord_id!r}, last_fm_user={self.last_fm_user!r})"


class Scrobble(Base):
    __tablename__ = "scrobble"

    id = Column(Integer, primary_key=True)

    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    album = Column(String)

    # in seconds
    listen_duration = Column(Integer, nullable=False)
    unix_timestamp = Column(Integer, nullable=False)

    user_id = Column(Integer, ForeignKey("user_account.id"))

    # each scrobble belongs to one single user
    # user = relationship("User", back_populates="scrobble_entries", uselist=False)
    user = relationship("User", uselist=False)

    def __repr__(self):
        return f"Scrobble({self.id=!r}, {self.title=!r}, {self.artist=!r}, {self.album=!r}, {self.listen_duration=!r}, {self.unix_timestamp=!r}, {self.user_id=!r})"


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


def store_scrobble(discord_id: int, scrobble: pylast.PlayedTrack) -> bool:
    """
    Returns True if the scrobble is sucesfully added
    to the scrobbles table, False otherwise.
    """

    scrobble_track: pylast.Track = scrobble.track

    new_scrobble = Scrobble(
        title=scrobble_track.get_name(),
        artist=scrobble_track.get_artist().get_name(),
        album=scrobble.album,
        listen_duration=int(scrobble_track.get_duration() / 1000),
        unix_timestamp=int(scrobble.timestamp),
    )

    with Session.begin() as session:

        user: User = session.query(User).filter_by(discord_id=discord_id).first()

        if not user:
            return False

        user.scrobble_entries.append(new_scrobble)

    return True


def store_scrobbles(discord_id: int, scrobbles: list[pylast.PlayedTrack]) -> bool:
    """
    Returns True if the scrobble is sucesfully added
    to the scrobbles table, False otherwise.
    """

    new_scrobbles: list[Scrobble] = []
    for scrobble in scrobbles:

        scrobble_track: pylast.Track = scrobble.track

        try:
            duration: int = scrobble_track.get_duration()

        except pylast.WSError:  # for tracks that error on duration for some odd reason
            duration: int = 0

        new_scrobble = Scrobble(
            title=scrobble_track.get_name(),
            artist=scrobble_track.get_artist().get_name(),
            album=scrobble.album,
            listen_duration=int(duration / 1000),
            unix_timestamp=int(scrobble.timestamp),
        )
        new_scrobbles.append(new_scrobble)

    with Session.begin() as session:

        user: User = session.query(User).filter_by(discord_id=discord_id).first()

        if not user:
            return False

        user.scrobble_entries.extend(new_scrobbles)

    return True


def update_user_scrobbles(
    network: pylast.LastFMNetwork, user_id: int, lfm_user: str
) -> None:
    """
    Attempt to retrieve most recent scrobbles that have not been
    stored in the database yet. If no scrobbles stored for user,
    try to grab entire history. Otherwise, grab all scrobbles
    since the latest stored scrobble for user.
    """

    print(f"storing *{user_id}*'s scrobbles")
    start = time.time()

    with Session.begin() as session:

        # find User.id for given last fm username (user param)
        user_id_query = session.query(User.id).filter_by(discord_id=user_id).subquery()

        # find the newest scrobble stored for them
        latest_timestamp: int = (
            session.query(func.max(Scrobble.unix_timestamp))
            .filter_by(user_id=user_id_query.c.id)
            .scalar()
        )

        user: pylast.User = network.get_user(lfm_user)

        if latest_timestamp:
            latest_timestamp += (
                1  # make sure it doesn't grab scrobble this timestamp is referring to
            )
            print("storing scrobbles since last timestamp in db!")
            # user: pylast.User = network.get_user(lfm_user)

            # get all tracks possible since last timestamp
            unstored_scrobbles: list[pylast.PlayedTrack] = user.get_recent_tracks(
                limit=None, time_from=latest_timestamp, stream=True
            )

            temp_tracks: list[pylast.PlayedTrack] = []
            for track in unstored_scrobbles:

                if len(temp_tracks) >= 100:
                    store_scrobbles(user_id, temp_tracks)
                    temp_tracks = list()  # remove all now stored tracks

                else:
                    temp_tracks.append(track)

            # add all scrobbles that weren't added in increments of 100 in loop
            if len(temp_tracks) > 0:
                store_scrobbles(user_id, temp_tracks)

        else:  # user has no scrobbles stored in database

            print("storing all user's scrobbles as they have no stored scrobbles!")

            unstored_scrobbles: list[pylast.PlayedTrack] = user.get_recent_tracks(
                None, stream=True
            )

            temp_tracks: list[pylast.PlayedTrack] = []
            for track in unstored_scrobbles:

                if len(temp_tracks) >= 100:
                    store_scrobbles(user_id, temp_tracks)
                    temp_tracks = list()  # remove all now stored tracks

                else:
                    temp_tracks.append(track)

            # add all scrobbles that weren't added in increments of 100 in loop
            if len(temp_tracks) > 0:
                store_scrobbles(user_id, temp_tracks)

    end = time.time()

    print(f"storing scrobbles took {end - start} seconds!")


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
