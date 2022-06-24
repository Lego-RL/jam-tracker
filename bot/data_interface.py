import discord

import sqlalchemy
from sqlalchemy import Column, ForeignKey, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

import datetime

import os
from os import pardir

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
    scrobble_entries = relationship("Scrobbles", back_populates="user")

    def __repr__(self):
        return f"User(id={self.id!r}, discord_id={self.discord_id!r}, last_fm_user={self.last_fm_user!r})"


class Scrobbles(Base):
    __tablename__ = "scrobbles"

    id = Column(Integer, primary_key=True)

    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    album = Column(String)

    # in seconds
    listen_duration = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=False)

    user_id = Column(Integer, ForeignKey("user_account.id"))

    # each scrobble belongs to one single user
    # user = relationship("User", back_populates="scrobble_entries", uselist=False)
    user = relationship("User", uselist=False)


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
