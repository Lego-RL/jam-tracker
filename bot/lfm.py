import traceback


import discord
import discord.commands
from discord import ApplicationContext, Embed
from discord.commands import slash_command, SlashCommandGroup, option
from discord.ext import commands

from discord.errors import CheckFailure

import pylast
import requests


from main import LFM_API_KEY, LFM_API_SECRET, LFM_USER, LFM_PASS

from data_interface import store_user, retrieve_lfm_username, get_correct_lfm_user

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


def has_set_lfm_user():
    """
    Decorator to check if discord user
    has already set their last.fm account
    with the bot.
    """

    def predicate(ctx):
        lfm_user = retrieve_lfm_username(ctx.user.id)

        return lfm_user is not None

    return commands.check(predicate)


class LastFM(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Bot = bot

        self.network = pylast.LastFMNetwork(
            api_key=LFM_API_KEY,
            api_secret=LFM_API_SECRET,
            # username=LFM_USER,
            # password_hash=LFM_PASS,
        )

    lfm = SlashCommandGroup(
        "lfm",
        "Commands related to last.fm.",
        guilds=guilds,
        guild_ids=guilds,
    )

    top = SlashCommandGroup(
        "top",
        "See info on your top artists, tracks, etc.",
        guilds=guilds,
        guild_ids=guilds,
    )

    pfp = SlashCommandGroup(
        "pfp",
        "Commands related to the bot's profile picture!",
        guilds=guilds,
        guild_ids=guilds,
    )

    @has_set_lfm_user()
    @slash_command(name="scrobbles", guilds=guilds)
    async def scrobbles(self, ctx: ApplicationContext, user: discord.User = None):
        """
        Display how many total scrobbles the user has.
        """

        # if user supplied, set lfm_user to their last.fm username & return if they have none set
        name: str = get_correct_lfm_user(ctx.user.id, user)

        if name is None:
            await ctx.respond(
                f"{ctx.user.mention}, this user does not have a last.fm username set!"
            )
            return

        user: pylast.User = self.network.get_user(name)
        await ctx.respond(
            f"{user.get_name()} has **{user.get_playcount()}** total scrobbles!"
        )

    @has_set_lfm_user()
    @slash_command(name="now", guilds=guilds)
    async def now_listening(self, ctx: ApplicationContext, user: discord.User = None):
        """
        Displays what you are currently listening to. Supply name with last.fm account
        you want to use.
        """

        # if user supplied, set lfm_user to their last.fm username & return if they have none set
        name = get_correct_lfm_user(ctx.user.id, user)

        if name is None:
            await ctx.respond(
                f"{ctx.user.mention}, this user does not have a last.fm username set!"
            )
            return

        user: pylast.User = self.network.get_user(name)

        track = user.get_now_playing()
        if track is None:

            await ctx.respond(
                f"**{user.get_name()}** is not currently listening to any track!"
            )
            return
        track.username = name

        embed_desc = f"{BLOB_JAMMIN} **[{track.get_title()}]({track.get_url()})** - {track.artist}\n{track.get_album().get_name()}"

        embed = discord.Embed(
            color=discord.Color.gold(),
            description=embed_desc,
        )

        image_url = user.get_image()

        if image_url:
            embed.set_author(
                name=f"{user.get_name()} - Now Listening",
                icon_url=image_url,
            )

        else:  # if user has no image leave off icon
            embed.set_author(
                name=f"{user.get_name()} - Now Listening",
            )

        embed.set_footer(
            text=f"{user.get_name()} has scrobbled this track {track.get_userplaycount()} times!"
        )
        embed.set_thumbnail(url=track.get_cover_image())

        await ctx.respond(embed=embed)

    @has_set_lfm_user()
    @slash_command(name="last", guilds=guilds)
    async def last_listened(
        self, ctx: ApplicationContext, user: discord.User = None
    ) -> None:
        """
        Displays the last song listened to. Supply name with last.fm account
        you want to use.
        """

        # if user supplied, set lfm_user to their last.fm username & return if they have none set
        name: str = get_correct_lfm_user(ctx.user.id, user)

        if name is None:
            await ctx.respond(
                f"{ctx.user.mention}, this user does not have a last.fm username set!"
            )
            return

        track: list[pylast.PlayedTrack] = self.network.get_user(name).get_recent_tracks(
            1
        )

        await ctx.respond(
            f"Last track played was **{track[0].track.title}** by {track[0].track.artist}!"
        )

    @has_set_lfm_user()
    @slash_command(name="recent", guilds=guilds)
    async def recent_tracks(
        self, ctx: ApplicationContext, user: discord.User = None
    ) -> None:
        """
        Display the user's last 5 played tracks.
        """

        # if user supplied, set lfm_user to their last.fm username & return if they have none set
        name: str = get_correct_lfm_user(ctx.user.id, user)

        if name is None:
            await ctx.respond(
                f"{ctx.user.mention}, this user does not have a last.fm username set!"
            )
            return

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
            if not now_playing and embed.thumbnail.url == discord.Embed.Empty:
                try:
                    cover_img_url = song_track.get_cover_image()
                    if cover_img_url is not None:
                        embed.set_thumbnail(url=cover_img_url)

                except IndexError:
                    pass

                except Exception:
                    print(traceback.format_exc())

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

    @has_set_lfm_user()
    @slash_command(name="discover", guilds=guilds)
    async def discover_new_from_favs(
        self,
        ctx: ApplicationContext,
        user: discord.User = None,
        include_remixes: bool = False,
    ) -> None:
        """
        Displays songs from your favorite artists that the user
        has never scrobbled before.
        """

        # if user supplied, set lfm_user to their last.fm username & return if they have none set
        name: str = get_correct_lfm_user(ctx.user.id, user)

        if name is None:
            await ctx.respond(
                f"{ctx.user.mention}, this user does not have a last.fm username set!"
            )
            return

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

    @lfm.command(
        name="set", description="Set last.fm username to use for all last.fm commands."
    )
    async def lfm_user_set(self, ctx: ApplicationContext, lfm_user: str) -> None:
        """
        Gets discord user's last.fm username to store for use with all
        last.fm related commands.
        """
        try:
            store_user(ctx.user.id, lfm_user)
            await ctx.respond(
                f"Successfully stored `{lfm_user}` as your last.fm account!"
            )

        except Exception as e:
            print(f"Oh no, error in lfm_user_set func!: {e}")

    @has_set_lfm_user()
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
        user: discord.User = None,
        period: str = "overall",
    ) -> None:
        """
        Display the user's top 10 artists, and how many scrobbles
        the user has for each.
        """

        # if user supplied, set lfm_user to their last.fm username & return if they have none set
        name: str = get_correct_lfm_user(ctx.user.id, user)

        if name is None:
            await ctx.respond(
                f"{ctx.user.mention}, this user does not have a last.fm username set!"
            )
            return

        lfm_period = PERIODS[period]

        user: pylast.User = self.network.get_user(name)
        fav_artists: list[pylast.TopItem] = user.get_top_artists(
            period=lfm_period, limit=10
        )

        artists_str: str = str()

        top_ten_scrobbles: int = 0
        for i in range(10):
            top_ten_scrobbles += int(fav_artists[i].weight)
            artists_str += f"\n{i+1}) [{fav_artists[i].item.name}]({fav_artists[i].item.get_url()}) - **{fav_artists[i].weight}** scrobbles"

        embed = discord.Embed(
            # title=f"{user.get_name()}'s Top 10 Artists ({period})",
            color=discord.Color.gold(),
            description=artists_str,
        )

        percent_scrobbles = (top_ten_scrobbles / user.get_playcount()) * 100

        embed.set_footer(
            text=f"These artists make up {percent_scrobbles:0.2f}% of {user.get_name()}'s total scrobbles!"
        )

        image_url = user.get_image()

        if image_url:
            embed.set_author(
                name=f"{user.get_name()}'s Top 10 Artists ({period})",
                icon_url=image_url,
            )

        else:
            embed.set_author(name=f"{user.get_name()}'s Top 10 Artists ({period})")

        await ctx.respond(embed=embed)

    @has_set_lfm_user()
    @top.command(name="tracks", description="See a list of your top ten tracks.")
    @option(
        name="period",
        type=str,
        description="Decides the period of time to find your top tracks for",
        choices=["7 days", "1 month", "3 months", "6 months", "12 months", "overall"],
        required=False,
        default="overall",
    )
    async def top_tracks(
        self,
        ctx: ApplicationContext,
        user: discord.User = None,
        period: str = "overall",
    ) -> None:
        """
        Display the user's top 10 tracks, and how many scrobbles
        the user has for each.
        """

        await ctx.defer()

        # if user supplied, set lfm_user to their last.fm username & return if they have none set
        name: str = get_correct_lfm_user(ctx.user.id, user)

        if name is None:
            await ctx.respond(
                f"{ctx.user.mention}, this user does not have a last.fm username set!"
            )
            return

        lfm_period = PERIODS[period]

        user: pylast.User = self.network.get_user(name)
        fav_tracks: list[pylast.TopItem] = user.get_top_tracks(
            period=lfm_period, limit=10
        )

        tracks_str: str = str()
        top_ten_scrobbles: int = 0
        for i in range(10):
            top_ten_scrobbles += fav_tracks[i].weight
            tracks_str += f"\n{i+1}) [{fav_tracks[i].item.get_name()}]({fav_tracks[i].item.get_url()}) - **{fav_tracks[i].weight}** scrobbles"

        embed = discord.Embed(
            color=discord.Color.gold(),
            description=tracks_str,
        )

        percent_scrobbles = (top_ten_scrobbles / user.get_playcount()) * 100

        embed.set_footer(
            text=f"These tracks make up {percent_scrobbles:0.2f}% of {user.get_name()}'s total scrobbles!"
        )

        image_url = user.get_image()

        if image_url:
            embed.set_author(
                name=f"{user.get_name()}'s Top 10 Tracks ({period})",
                icon_url=image_url,
            )

        else:
            embed.set_author(name=f"{user.get_name()}'s Top 10 Tracks ({period})")

        try:
            if cover_img := fav_tracks[0].item.get_cover_image():
                embed.set_thumbnail(url=cover_img)

        except IndexError:
            pass

        await ctx.respond(embed=embed)

    @pfp.command(
        name="update",
        description="Update the bot's profile picture to album art of your choice! Approved users only.",
    )
    async def pfp_change(self, ctx: ApplicationContext, album: str) -> None:
        """
        Update bot's profile picture to cover art of the given
        album, if the album is found.
        """

        # limit where command can be used
        approved_guilds = [938179110558105672, 315782312476409867]

        if ctx.guild_id not in approved_guilds:
            await ctx.respond(
                "You do not have permission to use this command, silly goose!"
            )
            return

        possibilities = pylast.AlbumSearch(album_name=album, network=self.network)
        first_result: pylast.Album = possibilities.get_next_page()[0]

        item_art_url = first_result.get_cover_image()
        item_art = requests.get(item_art_url).content

        await self.bot.user.edit(avatar=item_art)
        await ctx.respond(
            f"Successfully set the profile picture!\n`{first_result.get_name()} by {first_result.get_artist()}`"
        )

    async def cog_command_error(self, ctx: ApplicationContext, error: Exception):
        if isinstance(error, CheckFailure):
            await ctx.respond(
                f"{ctx.user.mention}, make sure you have set your last.fm username using `/lfm set [username]`!"
            )
        else:
            print(f"o no, error!\n{error}\n{traceback.format_exc()}")


def setup(bot: discord.Bot):
    bot.add_cog(LastFM(bot))
