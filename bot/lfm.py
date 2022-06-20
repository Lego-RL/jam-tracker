import discord
from discord.commands import slash_command
from discord.ext import commands

import pylast

from main import LFM_API_KEY, LFM_API_SECRET, LFM_USER, LFM_PASS

guilds = [315782312476409867]


class LastFM(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.network = pylast.LastFMNetwork(
            api_key=LFM_API_KEY,
            api_secret=LFM_API_SECRET,
            username=LFM_USER,
            password_hash=LFM_PASS,
        )

    @slash_command(name="now", guilds=guilds)
    async def now_listening(self, ctx, name: str = "Lego_RL"):
        """
        Displays what you are currently listening to. Supply name with last.fm account
        you want to use.
        """

        await ctx.respond(
            f"Now listening to **{self.network.get_user(name).get_now_playing().title}**"
        )

    @slash_command(name="last", guilds=guilds)
    async def last_listened(self, ctx, name: str = "Lego_RL") -> None:
        """
        Displays the last song listened to. Supply name with last.fm account
        you want to use.
        """

        track: list[pylast.PlayedTrack] = self.network.get_user(name).get_recent_tracks(
            1
        )

        await ctx.respond(f"Last track played was **{track[0].track.title}**.")

    @slash_command(name="discover", guilds=guilds)
    async def discover_new_from_favs(
        self, ctx, name: str = "Lego_RL", include_remixes: bool = False
    ) -> None:
        """
        Displays songs from your favorite artists that the user
        has never scrobbled before.
        """

        user = self.network.get_user(name)

        fav_artists: list[pylast.Artist] = user.get_top_artists(
            period=pylast.PERIOD_3MONTHS, limit=3
        )

        to_suggest: list[pylast.Track] = []

        for artist, _ in fav_artists:
            songs: list[tuple(pylast.Track, int)] = artist.get_top_tracks(limit=100)
            songs.reverse()  # search through least listened tracks first

            for song, _ in songs:
                if not include_remixes and "remix" in str(song).lower():
                    continue

                if song.get_userplaycount() == 0:
                    to_suggest.append(song)
                    break

        rtn = ""
        for i, song in enumerate(to_suggest):
            rtn += f"\n{i+1}) {song.get_name()} by {song.get_artist()}"

        await ctx.respond(f"Here are your suggestions:\n{rtn}")


def setup(bot: discord.Bot):
    bot.add_cog(LastFM(bot))
