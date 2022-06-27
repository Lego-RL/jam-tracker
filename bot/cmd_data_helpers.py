from sqlalchemy import func, asc, desc

from data_interface import Session, User, Scrobble


class StrippedTrack:
    """
    Custom class to store a track's data, named Stripped
    because it only hasessential data for the track
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


def get_five_recent_tracks(lfm_user: str) -> list[StrippedTrack]:
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
            .limit(5)
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

            track_obj = StrippedTrack(
                title=track.title,
                artist=track.artist,
                album=track.album,
                unix_timestamp=track.unix_timestamp,
                lfm_url=track.lfm_url,
                track_plays=track_plays,
            )
            stripped_tracks.append(track_obj)

    return stripped_tracks


# testing purposes
if __name__ == "__main__":
    get_five_recent_tracks("BVeil")
