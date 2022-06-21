import string
import discord
from discord import ApplicationContext, Embed
from discord.commands import slash_command, SlashCommandGroup, option
from discord.ext import commands

import pylast

from main import LFM_API_KEY, LFM_API_SECRET, LFM_USER, LFM_PASS

guilds = [315782312476409867, 938179110558105672]

PERIODS = {
    "7 days": pylast.PERIOD_7DAYS,
    "1 month": pylast.PERIOD_1MONTH,
    "3 months": pylast.PERIOD_3MONTHS,
    "6 months": pylast.PERIOD_6MONTHS,
    "12 months": pylast.PERIOD_12MONTHS,
    "overall": pylast.PERIOD_OVERALL,
}


class LastFM(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.network = pylast.LastFMNetwork(
            api_key=LFM_API_KEY,
            api_secret=LFM_API_SECRET,
            username=LFM_USER,
            password_hash=LFM_PASS,
        )

    top = SlashCommandGroup(
        "top",
        "See info on your top artists, tracks, etc.",
        guilds=guilds,
        guild_ids=guilds,
    )

    @slash_command(name="scrobbles", guilds=guilds)
    async def scrobbles(self, ctx, name: str = "Lego_RL"):
        """
        Display how many total scrobbles the user has.
        """

        user = self.network.get_user(name)
        await ctx.respond(
            f"{user.get_name()} has **{user.get_playcount()}** total scrobbles!"
        )

    @slash_command(name="now", guilds=guilds)
    async def now_listening(self, ctx, name: str = "Lego_RL"):
        """
        Displays what you are currently listening to. Supply name with last.fm account
        you want to use.
        """

        track = self.network.get_user(name).get_now_playing()

        await ctx.respond(f"Now listening to **{track.title}** by {track.artist}!")

    @slash_command(name="last", guilds=guilds)
    async def last_listened(self, ctx, name: str = "Lego_RL") -> None:
        """
        Displays the last song listened to. Supply name with last.fm account
        you want to use.
        """

        track: list[pylast.PlayedTrack] = self.network.get_user(name).get_recent_tracks(
            1
        )

        await ctx.respond(
            f"Last track played was **{track[0].track.title}** by {track[0].track.artist}!"
        )

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

                if "video" in str(song).lower():
                    continue

                if not include_remixes and "remix" in str(song).lower():
                    continue

                if song.get_userplaycount() == 0:
                    to_suggest.append(song)
                    break

        rtn = ""
        for i, song in enumerate(to_suggest):
            rtn += f"\n{i+1}) {song.get_name()} by {song.get_artist()}"

        await ctx.respond(f"Here are your suggestions:\n{rtn}")

    @top.command(name="artists", description="See a list of your top ten artists.")
    @option(
        name="period",
        type=str,
        description="Decides the period of time to find your top artists for",
        choices=["7 days", "1 month", "3 months", "6 months", "12 months", "overall"],
        required=False,
        default="overall",
    )
    async def top_artists(
        self,
        ctx: ApplicationContext,
        name: str = "Lego_RL",
        period: str = "overall",
    ) -> None:
        """
        Display the user's top 10 artists, and how many scrobbles
        the user has for each.
        """

        lfm_period = PERIODS[period]

        user: pylast.User = self.network.get_user(name)
        fav_artists: list[pylast.TopItem] = user.get_top_artists(
            period=lfm_period, limit=10
        )

        artists_str: str = str()
        for i in range(10):
            artists_str += f"\n{i+1}) [{fav_artists[i].item.name}]({fav_artists[i].item.get_url()}) - **{fav_artists[i].weight}** scrobbles"

        embed = discord.Embed(
            title=f"{user.get_name()}'s Top 10 Artists ({period})",
            color=discord.Color.gold(),
            description=artists_str,
        )

        embed.set_thumbnail(url=ctx.user.avatar.url)

        await ctx.respond(embed=embed)


def setup(bot: discord.Bot):
    bot.add_cog(LastFM(bot))
