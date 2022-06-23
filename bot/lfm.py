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

BLOB_JAMMIN: str = "<a:blobjammin:988683824860921857>"  # emote


class LastFM(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.network = pylast.LastFMNetwork(
            api_key=LFM_API_KEY,
            api_secret=LFM_API_SECRET,
            # username=LFM_USER,
            # password_hash=LFM_PASS,
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
    async def now_listening(self, ctx: ApplicationContext, name: str = "Lego_RL"):
        """
        Displays what you are currently listening to. Supply name with last.fm account
        you want to use.
        """

        track = self.network.get_user(name).get_now_playing()

        await ctx.respond(f"Now listening to **{track.title}** by {track.artist}!")

    @slash_command(name="last", guilds=guilds)
    async def last_listened(
        self, ctx: ApplicationContext, name: str = "Lego_RL"
    ) -> None:
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

    @slash_command(name="recent", guilds=guilds)
    async def recent_tracks(
        self, ctx: ApplicationContext, name: str = "Lego_RL"
    ) -> None:
        """
        Display the user's last 5 played tracks.
        """

        await ctx.defer()

        user: pylast.User = self.network.get_user(name)

        now_playing: pylast.Track = user.get_now_playing()
        num_get = (
            4 if now_playing else 5
        )  # only get 4 tracks if user is already playing a 5th

        track: list[pylast.PlayedTrack] = user.get_recent_tracks(num_get)

        embed = discord.Embed(
            color=discord.Color.gold(),
        )

        image_url = user.get_image()

        if image_url:
            embed.set_author(
                name=f"{user.get_name()}'s recently played tracks",
                icon_url=image_url,
            )

        else:  # if user has no image leave off icon
            embed.set_author(
                name=f"{user.get_name()}'s recently played tracks",
            )

        embed_string: str = ""
        if now_playing:

            embed.set_thumbnail(url=now_playing.get_cover_image())

            # off set the song nums by 2 if listening song currently
            # one to start counting from 1, and 2 if now_playing is the #1
            number_offset: int = 2

            track_name, track_artist = now_playing.get_name(), now_playing.get_artist()
            embed_string += f"{BLOB_JAMMIN} **[{track_name}]({now_playing.get_url()})** - {track_artist}\n"

            if (np_track_album := now_playing.get_album()) is not None:
                embed_string += f"{np_track_album.get_name()} | {now_playing.get_userplaycount()} scrobbles\n\n"

            else:
                embed_string += f"{now_playing.get_playcount()} scrobbles\n\n"

        else:
            number_offset: int = 1

        for i, song in enumerate(track):

            song_track: pylast.Track = song.track
            song_track.username = name

            # if no cover art is set bc no now_playing song atm, set to last played songs art
            if i == 0 and not now_playing:
                embed.set_thumbnail(url=song_track.get_cover_image())

            embed_string += f"{i+number_offset}) **[{song_track.get_name()}]({song_track.get_url()})** - {song_track.get_artist()}\n"

            if song.album is not None:
                embed_string += (
                    f"{song.album} | {song_track.get_userplaycount()} scrobbles\n\n"
                )

            else:
                embed_string += f"{song_track.get_userplaycount()} scrobbles\n\n"

        embed.description = embed_string
        embed.set_footer(
            text=f"{user.get_name()} has {user.get_playcount()} total scrobbles!"
        )

        await ctx.respond(embed=embed)

    @slash_command(name="discover", guilds=guilds)
    async def discover_new_from_favs(
        self,
        ctx: ApplicationContext,
        name: str = "Lego_RL",
        include_remixes: bool = False,
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

        songs_str = ""
        for i, song in enumerate(to_suggest):
            songs_str += (
                f"\n{i+1}) [{song.get_name()}]({song.get_url()}) - {song.get_artist()}"
            )

        embed = discord.Embed(
            title=f"Listening suggestions for your top artists!",
            color=discord.Color.gold(),
            description=songs_str,
        )

        embed.set_thumbnail(url=ctx.user.avatar.url)

        await ctx.respond(embed=embed)

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
