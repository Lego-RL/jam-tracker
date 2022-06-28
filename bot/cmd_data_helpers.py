import datetime

import pylast
from sqlalchemy import func, asc, desc


from data_interface import Session, User, Scrobble


class StrippedTrack:
    """
    Custom class to store a track's data, named Stripped
    because it only has essential data for the track
    versus a pylast.Track object.
    """

    def __init__(
        self,
        title: str,
        artist: str,
        album: str,
        lfm_url: str,
        unix_timestamp: int,
        track_plays: int,
    ):
        self.title = title
        self.artist = artist
        self.album = album
        self.lfm_url = lfm_url
        self.unix_timestamp = unix_timestamp
        self.track_plays = track_plays

    def __repr__(self) -> str:
        return f"StrippedTrack({self.title=}, {self.artist=}, {self.album=}, {self.unix_timestamp=}, {self.track_plays=})"


class StrippedArtist:
    """
    Custom class to store an artist's data, named Stripped
    because it only has essential data for the artist
    versus a pylast.Artist object.
    """

    def __init__(self, artist: str, artist_plays: int):
        self.artist = artist
        self.artist_plays = artist_plays


def generate_stripped_track(track: Scrobble, track_plays: int) -> StrippedTrack:
    """
    Generate a StrippedTrack object from a Scrobble object.
    """

    track_obj = StrippedTrack(
        title=track.title,
        artist=track.artist,
        album=track.album,
        unix_timestamp=track.unix_timestamp,
        lfm_url=track.lfm_url,
        track_plays=track_plays,
    )

    return track_obj


def get_x_recent_tracks(lfm_user: str, num_tracks: int) -> list[StrippedTrack]:
    """
    Retrieve the last five tracks scrobbled by a user from
    the database (assumed to be up to date) as StrippedTrack
    objects.
    """

    stripped_tracks: list[StrippedTrack] = []
    with Session.begin() as session:
        user_id_query = (
            session.query(User.id).filter_by(last_fm_user=lfm_user).subquery()
        )

        tracks: list[Scrobble] = (
            session.query(Scrobble)
            .order_by(desc(Scrobble.unix_timestamp))
            .filter_by(user_id=user_id_query.c.id)
            .limit(num_tracks)
            .all()
        )

        if tracks is None:
            return None

        for track in tracks:
            user_id_query = (
                session.query(User.id).filter_by(last_fm_user=lfm_user).subquery()
            )

            track_plays = (
                session.query(Scrobble)
                .filter_by(user_id=user_id_query.c.id)
                .filter_by(title=track.title)
                .count()
            )

            track_obj: StrippedTrack = generate_stripped_track(track, track_plays)

            stripped_tracks.append(track_obj)

    return stripped_tracks


def get_x_top_tracks(
    lfm_user: str, num_tracks: int, unix_timestamp: int = None
) -> list[StrippedTrack]:
    """
    Return top x tracks based on number of scrobbles the
    user has for each song.
    """

    stripped_tracks: list[StrippedTrack] = []
    with Session.begin() as session:
        user_id_query = (
            session.query(User.id).filter_by(last_fm_user=lfm_user).subquery()
        )

        if unix_timestamp:
            tracks: list[Scrobble] = (
                session.query(Scrobble)
                .filter_by(user_id=user_id_query.c.id)
                .filter(Scrobble.unix_timestamp > unix_timestamp)
                .group_by(Scrobble.title)
                .order_by(desc(func.count(Scrobble.title)))
                .limit(num_tracks)
                .all()
            )

        else:
            tracks: list[Scrobble] = (
                session.query(Scrobble)
                .filter_by(user_id=user_id_query.c.id)
                .group_by(Scrobble.title)
                .order_by(desc(func.count(Scrobble.title)))
                .limit(num_tracks)
                .all()
            )

        if tracks is None:
            return None

        for track in tracks:
            user_id_query = (
                session.query(User.id).filter_by(last_fm_user=lfm_user).subquery()
            )

            if unix_timestamp:
                track_plays = (
                    session.query(Scrobble)
                    .filter_by(user_id=user_id_query.c.id)
                    .filter_by(title=track.title)
                    .filter(Scrobble.unix_timestamp > unix_timestamp)
                    .count()
                )
            else:
                track_plays = (
                    session.query(Scrobble)
                    .filter_by(user_id=user_id_query.c.id)
                    .filter_by(title=track.title)
                    .count()
                )

            track_obj: StrippedTrack = generate_stripped_track(track, track_plays)

            stripped_tracks.append(track_obj)

    return stripped_tracks


def get_x_top_artists(lfm_user: str, num_artists: int) -> list[StrippedArtist]:
    """
    Return top x artists based on number of scrobbles the
    user has for each artist.
    """

    stripped_artists: list[StrippedArtist] = []
    with Session.begin() as session:
        user_id_query = (
            session.query(User.id).filter_by(last_fm_user=lfm_user).subquery()
        )

        artists: list[Scrobble] = (
            session.query(Scrobble)
            .filter_by(user_id=user_id_query.c.id)
            .group_by(Scrobble.artist)
            .order_by(desc(func.count(Scrobble.artist)))
            .limit(num_artists)
            .all()
        )

        if artists is None:
            return None

        for artist in artists:
            user_id_query = (
                session.query(User.id).filter_by(last_fm_user=lfm_user).subquery()
            )

            artist_plays = (
                session.query(Scrobble)
                .filter_by(user_id=user_id_query.c.id)
                .filter_by(artist=artist.artist)
                .count()
            )

            artist_obj: StrippedArtist = StrippedArtist(artist.artist, artist_plays)

            stripped_artists.append(artist_obj)

    return stripped_artists


def get_relative_unix_timestamp(period: str) -> int:
    """
    Takes a time period string and translates it
    into a unix timestamp relative to the current time.
    """

    delta: datetime.timedelta = None

    match period:

        case "1 day":
            delta = datetime.timedelta(days=1)
        case pylast.PERIOD_7DAYS:
            delta = datetime.timedelta(days=7)
        case pylast.PERIOD_1MONTH:
            delta = datetime.timedelta(weeks=4)
        case pylast.PERIOD_3MONTHS:
            delta = datetime.timedelta(weeks=12)
        case pylast.PERIOD_12MONTHS:
            delta = datetime.timedelta(weeks=52)
        case _:
            delta = None

    if delta is None:
        return None

    return int((datetime.datetime.now() - delta).timestamp())
