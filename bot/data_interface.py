import discord
import pylast
import sqlalchemy
from sqlalchemy import Column, ForeignKey, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

import datetime
import os

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


def store_scrobble(discord_id: int, scrobble: pylast.PlayedTrack = None) -> bool:
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


def retrieve_lfm_username(discord_id: int, update_scrobble_data: bool = False) -> str:
    """
    Retrieve's last.fm username associated with discord
    user id.
    """

    with Session.begin() as session:
        user: str = (
            session.query(User.last_fm_user).filter_by(discord_id=discord_id).scalar()
        )

        if user:
            if update_scrobble_data:
                pass
                # update_user_scrobbles(user))

            return user

        return None  # user not found


def get_correct_lfm_user(invoker_id: int, user: discord.User) -> str:
    """
    Returns last.fm username of the command invoker if no user
    argument is supplied, otherwise returns last.fm username
    belonging to the discord user given.
    """

    if user:
        return retrieve_lfm_username(user.id)

    else:
        return retrieve_lfm_username(invoker_id)
