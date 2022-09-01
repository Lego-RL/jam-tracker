import traceback

import discord
import discord.commands
from discord import ApplicationContext
from discord.commands import slash_command, SlashCommandGroup, option
from discord.ext import commands

from discord import CheckFailure
from discord.ext.commands.errors import CommandOnCooldown

import pylast

import datetime
import requests

from data_interface import (
    store_user,
    update_user,
    retrieve_lfm_username,
    get_lfm_username,
    get_lfm_username,
    get_number_user_scrobbles_stored,
)
from image import combine_images, update_embed_color
from io import BytesIO
from main import LFM_API_KEY, LFM_API_SECRET
from spotify import get_artist_image_url, get_track_image_url, get_album_image_url
from PIL import Image

from cmd_data_helpers import StrippedTrack, StrippedArtist, StrippedAlbum
from cmd_data_helpers import get_artist_lfm_link, get_album_lfm_link
from cmd_data_helpers import (
    get_x_recent_tracks,
    get_x_top_tracks,
    get_x_top_artists,
    get_x_top_albums,
    get_relative_unix_timestamp,
    get_single_track_info,
    get_discord_relative_timestamp,
)

guilds = [
    315782312476409867,
    938179110558105672,
    957732024859365466,
    108262903802511360,
]

PERIODS = {
    "1 day": "1 day",
    "7 days": pylast.PERIOD_7DAYS,
    "1 month": pylast.PERIOD_1MONTH,
    "3 months": pylast.PERIOD_3MONTHS,
    "6 months": pylast.PERIOD_6MONTHS,
    "12 months": pylast.PERIOD_12MONTHS,
    "overall": pylast.PERIOD_OVERALL,
}

CMD_TIME_CHOICES = list(PERIODS.keys())

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
        )

    lfm = SlashCommandGroup(
        "lfm",
        "Commands related to last.fm.",
    )

    top = SlashCommandGroup(
        "top",
        "See info on your top artists, tracks, etc.",
    )

    chart = SlashCommandGroup(
        "chart",
        "View charts on your top artists or tracks!",
    )

    pfp = SlashCommandGroup(
        "pfp",
        "Commands related to the bot's profile picture!",
    )

    @has_set_lfm_user()
    @slash_command(name="scrobbles")
    async def scrobbles(self, ctx: ApplicationContext, user: discord.User = None):
        """
        Display how many total scrobbles the user has.
        """

        await ctx.defer()

        user_id = ctx.user.id if user is None else user.id

        # name: str = get_lfm_username(self.network, ctx.user.id, user)

        # if name is None:
        #     await ctx.respond(
        #         f"{ctx.user.mention}, this user does not have a last.fm username set!"
        #     )
        #     return

        num_scrobbles = get_number_user_scrobbles_stored(user_id)

        # await ctx.respond(f"{name} has **{num_scrobbles}** total scrobbles!")
        await ctx.respond(f"u has **{num_scrobbles}** total scrobbles!")

    @has_set_lfm_user()
    @slash_command(name="now")
    async def now_listening(self, ctx: ApplicationContext, user: discord.User = None):
        """
        Displays what you are currently listening to. Supply name with last.fm account
        you want to use.
        """

        await ctx.defer()

        # if user supplied, set lfm_user to their last.fm username & return if they have none set
        name = get_lfm_username(ctx.user.id, user)

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

        try:
            embed.set_footer(
                text=f"{user.get_name()} has scrobbled this track {track.get_userplaycount()} times!"
            )
        except pylast.WSError as e:  # occurs sometimes when can't get track playcount? look more in depth later
            print(f"Error, likely due to failed retrieving track.get_userplaycount()")

        track_image_url = track.get_cover_image()

        if track_image_url:
            embed.set_thumbnail(url=track_image_url)
            embed = update_embed_color(embed)

        await ctx.respond(embed=embed)

    @has_set_lfm_user()
    @slash_command(name="recent")
    async def recent_tracks(
        self, ctx: ApplicationContext, user: discord.User = None
    ) -> None:
        """
        Display the user's last 5 played tracks.
        """

        await ctx.defer()

        # if user supplied, set lfm_user to their last.fm username & return if they have none set
        name: str = get_lfm_username(ctx.user.id, user)

        if name is None:
            await ctx.respond(
                f"{ctx.user.mention}, this user does not have a last.fm username set!"
            )
            return

        stripped_tracks: list[StrippedTrack] = get_x_recent_tracks(name, 5)

        if len(stripped_tracks) == 0:
            await ctx.respond(f"{ctx.user.mention}, this user has no scrobbled tracks!")
            return

        user: pylast.User = self.network.get_user(name)

        now_playing: pylast.Track = user.get_now_playing()
        num_get = (
            4 if now_playing else 5
        )  # only get 4 tracks if user is already playing a 5th

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
            cover_image: str = now_playing.get_cover_image()

            embed.set_thumbnail(url=cover_image)

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
            cover_image: str = None

        for i, song in enumerate(stripped_tracks):
            if number_offset == 2 and i == 4:
                break

            if not embed.thumbnail.url and i == 0:
                try:
                    cover_image_url = get_track_image_url(song.title, song.artist)
                    embed.set_thumbnail(url=cover_image_url)

                except Exception as e:
                    traceback.format_exc()

            embed_string += f"{i+number_offset}) **[{song.title}]({song.lfm_url})** - {song.artist}\n"
            embed_string += f"{song.album} | {song.track_plays} scrobbles\n\n"

        embed.description = embed_string
        embed.set_footer(
            text=f"{user.get_name()} has {user.get_playcount()} total scrobbles!"
        )
        embed = update_embed_color(embed)

        await ctx.respond(embed=embed)

    @lfm.command(
        name="set", description="Set last.fm username to use for all last.fm commands."
    )
    # @commands.cooldown(1, (60 * 10), commands.BucketType.user)
    async def lfm_user_set(self, ctx: ApplicationContext, lfm_user: str) -> None:
        """
        Gets discord user's last.fm username to store for use with all
        last.fm related commands.
        """

        user: pylast.User = self.network.get_user(lfm_user)

        try:
            user.get_recent_tracks(limit=1)

        except:
            await ctx.respond(
                "Unable to fetch last.fm profile. Did you misspell your account name?",
                ephemeral=True,
            )
            ctx.command.reset_cooldown(ctx)
            return

        result: bool = store_user(ctx.user.id, lfm_user)

        if result:
            await ctx.respond(
                f"Successfully stored `{lfm_user}` as your last.fm account!",
                ephemeral=True,
            )
        else:
            update_result: bool = update_user(ctx.user.id, lfm_user)

            # successful update
            if update_result:
                await ctx.respond(
                    f"Successfully updated your stored last.fm account to `{lfm_user}`!",
                    ephemeral=True,
                )

            # trying to set to the same username already set
            else:
                await ctx.respond(
                    f"You're trying to set your last.fm username to the same one already stored, silly goose!",
                    ephemeral=True,
                )
                ctx.command.reset_cooldown(ctx)
                return

    @has_set_lfm_user()
    @top.command(name="artists", description="See a list of your top ten artists.")
    @option(
        name="period",
        type=str,
        description="Decides the period of time to find your top artists for",
        choices=CMD_TIME_CHOICES,
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

        await ctx.defer()

        # if user supplied, set lfm_user to their last.fm username & return if they have none set
        name: str = get_lfm_username(ctx.user.id, user)
        discord_id = ctx.user.id if user is None else user.id

        if name is None:
            await ctx.respond(
                f"{ctx.user.mention}, this user does not have a last.fm username set!"
            )
            return

        embed = discord.Embed(color=discord.Color.gold())
        user: pylast.User = self.network.get_user(name)

        lfm_period = PERIODS[period]
        relative_timestamp: int = get_relative_unix_timestamp(lfm_period)

        if relative_timestamp is None:
            relative_timestamp = 0

        stripped_artists: list[StrippedArtist] = get_x_top_artists(
            name, 10, relative_timestamp
        )

        if len(stripped_artists) == 0:
            await ctx.respond(
                f"{ctx.user.mention}, this user has no scrobbles over the period of **{period}**!"
            )
            return

        artists_str: str = str()

        top_ten_scrobbles: int = 0
        for i, artist in enumerate(stripped_artists):
            top_ten_scrobbles += int(artist.artist_plays)

            if i == 0:
                artist_image_url: str = get_artist_image_url(artist.artist)

                if artist_image_url:
                    embed.set_thumbnail(url=artist_image_url)
                    embed = update_embed_color(embed)

            artist_link: str = get_artist_lfm_link(artist.artist)
            artists_str += f"\n{i+1}) [{artist.artist}]({artist_link}) - **{artist.artist_plays}** scrobbles"

        embed.description = artists_str

        percent_scrobbles = (
            top_ten_scrobbles / get_number_user_scrobbles_stored(discord_id)
        ) * 100

        embed.set_footer(
            text=f"These artists make up {percent_scrobbles:0.2f}% of {name}'s total scrobbles!"
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
        choices=CMD_TIME_CHOICES,
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
        name: str = get_lfm_username(ctx.user.id, user)
        discord_id = ctx.user.id if user is None else user.id

        if name is None:
            await ctx.respond(
                f"{ctx.user.mention}, this user does not have a last.fm username set!"
            )
            return

        embed = discord.Embed(color=discord.Color.gold())
        user: pylast.User = self.network.get_user(name)

        lfm_period = PERIODS[period]
        relative_timestamp: int = get_relative_unix_timestamp(lfm_period)

        # set to 0 since any song after unix time "0" includes all songs anyway
        if relative_timestamp is None:
            relative_timestamp = 0

        stripped_tracks: list[StrippedTrack] = get_x_top_tracks(
            name, 10, relative_timestamp
        )

        if len(stripped_tracks) == 0:
            await ctx.respond(
                f"{ctx.user.mention}, this user has no scrobbles over the period of **{period}**!"
            )
            return

        tracks_str: str = str()
        top_ten_scrobbles: int = 0
        for i, track in enumerate(stripped_tracks):
            top_ten_scrobbles += track.track_plays

            if i == 0:
                track_image_url = get_track_image_url(track.title, track.artist)

                if track_image_url:
                    embed.set_thumbnail(url=track_image_url)
                    embed = update_embed_color(embed)

            tracks_str += f"\n{i+1}) [{track.title}]({track.lfm_url}) - **{track.track_plays}** scrobbles"

        embed.description = tracks_str

        percent_scrobbles = (
            top_ten_scrobbles / get_number_user_scrobbles_stored(discord_id)
        ) * 100

        embed.set_footer(
            text=f"These tracks make up {percent_scrobbles:0.2f}% of {name}'s total scrobbles!"
        )

        image_url = user.get_image()

        if image_url:
            embed.set_author(
                name=f"{user.get_name()}'s Top 10 Tracks ({period})",
                icon_url=image_url,
            )
        else:
            embed.set_author(name=f"{user.get_name()}'s Top 10 Tracks ({period})")

        await ctx.respond(embed=embed)

    @has_set_lfm_user()
    @top.command(name="albums", description="See a list of your top ten albums.")
    @option(
        name="period",
        type=str,
        description="Decides the period of time to find your top albums for",
        choices=CMD_TIME_CHOICES,
        required=False,
        default="overall",
    )
    async def top_albums(
        self,
        ctx: ApplicationContext,
        user: discord.User = None,
        period: str = "overall",
    ) -> None:
        """
        Display the user's top 10 album, and how many scrobbles
        the user has for each.
        """

        await ctx.defer()

        # if user supplied, set lfm_user to their last.fm username & return if they have none set
        name: str = get_lfm_username(ctx.user.id, user)
        discord_id = ctx.user.id if user is None else user.id

        if name is None:
            await ctx.respond(
                f"{ctx.user.mention}, this user does not have a last.fm username set!"
            )
            return

        embed = discord.Embed(color=discord.Color.gold())
        user: pylast.User = self.network.get_user(name)

        lfm_period = PERIODS[period]
        relative_timestamp: int = get_relative_unix_timestamp(lfm_period)

        # set to 0 since any song after unix time "0" includes all songs anyway
        if relative_timestamp is None:
            relative_timestamp = 0

        stripped_albums: list[StrippedAlbum] = get_x_top_albums(
            name, 10, relative_timestamp
        )

        if len(stripped_albums) == 0:
            await ctx.respond(
                f"{ctx.user.mention}, this user has no scrobbles over the period of **{period}**!"
            )
            return

        albums_str: str = str()
        top_ten_scrobbles: int = 0
        for i, album in enumerate(stripped_albums):
            top_ten_scrobbles += album.album_plays

            if i == 0:
                album_image_url = get_album_image_url(album.album, album.artist)

                if album_image_url:
                    embed.set_thumbnail(url=album_image_url)
                    embed = update_embed_color(embed)

            album_link: str = get_album_lfm_link(album.artist, album.album)
            albums_str += f"\n{i+1}) [{album.album}]({album_link}) - **{album.album_plays}** scrobbles"

        embed.description = albums_str

        percent_scrobbles = (
            top_ten_scrobbles / get_number_user_scrobbles_stored(discord_id)
        ) * 100

        embed.set_footer(
            text=f"These albums make up {percent_scrobbles:0.2f}% of {name}'s total scrobbles!"
        )

        image_url = user.get_image()

        if image_url:
            embed.set_author(
                name=f"{user.get_name()}'s Top 10 Albums ({period})",
                icon_url=image_url,
            )
        else:
            embed.set_author(name=f"{user.get_name()}'s Top 10 Albums ({period})")

        await ctx.respond(embed=embed)

    @has_set_lfm_user()
    @slash_command(name="track", description="See info about a single track.")
    async def track_info(
        self,
        ctx: ApplicationContext,
        track_title: str,
        track_artist: str = None,
        user: discord.User = None,
    ) -> None:
        """
        Display info about a single track.
        """

        # if user supplied, set lfm_user to their last.fm username & return if they have none set
        name: str = get_lfm_username(ctx.user.id, user)
        discord_id = ctx.user.id if user is None else user.id

        if name is None:
            await ctx.respond(
                f"{ctx.user.mention}, this user does not have a last.fm username set!"
            )
            return

        track_data = get_single_track_info(discord_id, track_title, track_artist)

        if track_data is None:
            await ctx.respond(f"{ctx.user.mention}, unable to find given track!")
            return

        try:
            stripped_track: StrippedTrack = track_data[0]
            if stripped_track is None:
                raise ValueError

            track_plays: int = track_data[1]
            image_url: str = track_data[2]

        except (IndexError, ValueError):
            await ctx.respond("Unable to find track!")
            return

        user: pylast.User = self.network.get_user(name)

        embed = discord.Embed(
            color=discord.Color.gold(),
        )

        user_image = user.get_image()

        if user_image:
            embed.set_author(
                name=f"Track info | {stripped_track.artist} - **{stripped_track.title}**",
                icon_url=user_image,
            )

        else:
            embed.set_author(
                name=f"Track info | {stripped_track.artist} - {stripped_track.title}"
            )

        if image_url:
            embed.set_thumbnail(url=image_url)
            embed = update_embed_color(embed)

        desc_str = f"""__Your data__:
        
        Total plays: {track_plays}
        
        """

        embed.description = desc_str

        await ctx.respond(embed=embed)

    @has_set_lfm_user()
    @chart.command(name="artists", description="View a chart of your top artists. ")
    @option(
        name="period",
        type=str,
        description="Decides the period of time to find your top artists for",
        choices=CMD_TIME_CHOICES,
        required=False,
        default="overall",
    )
    async def artist_chart(
        self,
        ctx: ApplicationContext,
        user: discord.User = None,
        period: str = "overall",
    ) -> None:
        """
        Displays a 3x3 chart of the user's top 9 artists.
        """

        await ctx.defer()

        # if user supplied, set lfm_user to their last.fm username & return if they have none set
        name: str = get_lfm_username(ctx.user.id, user)

        if name is None:
            await ctx.respond(
                f"{ctx.user.mention}, this user does not have a last.fm username set!"
            )
            return

        lfm_period = PERIODS[period]
        relative_timestamp: int = get_relative_unix_timestamp(lfm_period)

        if relative_timestamp is None:
            relative_timestamp = 0

        NUM_ARTISTS = 9
        top_artists: list[StrippedArtist] = get_x_top_artists(
            name, NUM_ARTISTS + 5, relative_timestamp
        )

        top_artist_urls: list[str] = []
        top_artist_names: list[str] = []
        index: int = 0
        while len(top_artist_urls) < NUM_ARTISTS and index < len(top_artists):
            artist_name = top_artists[index].artist

            if (artist_image_url := get_artist_image_url(artist_name)) is not None:
                top_artist_urls.append(artist_image_url)
                top_artist_names.append(artist_name)
            index += 1

        pil_img_chart: Image = combine_images(top_artist_names, top_artist_urls)

        with BytesIO() as image_binary:
            pil_img_chart.save(image_binary, "PNG")
            image_binary.seek(0)
            await ctx.respond(
                file=discord.File(fp=image_binary, filename=f"{user}_artist_chart.png")
            )

        # send embed describing parameters
        embed = discord.Embed(
            title=f"Artist chart for {user.name if user else ctx.user.name} - {period.title()}"
        )

        # temporarily set thumbnail to get embed color the same as the first artist pic
        embed.set_thumbnail(url=top_artist_urls[0])
        embed = update_embed_color(embed)
        embed.remove_thumbnail()

        await ctx.send(embed=embed)

    @has_set_lfm_user()
    @chart.command(name="albums", description="View a chart of your top albums. ")
    @option(
        name="period",
        type=str,
        description="Decides the period of time to find your top albums for",
        choices=CMD_TIME_CHOICES,
        required=False,
        default="overall",
    )
    async def album_chart(
        self,
        ctx: ApplicationContext,
        user: discord.User = None,
        period: str = "overall",
    ) -> None:
        """
        Displays a 3x3 chart of the user's top 9 albums.
        """

        await ctx.defer()

        # if user supplied, set lfm_user to their last.fm username & return if they have none set
        name: str = get_lfm_username(ctx.user.id, user)

        if name is None:
            await ctx.respond(
                f"{ctx.user.mention}, this user does not have a last.fm username set!"
            )
            return

        lfm_period = PERIODS[period]
        relative_timestamp: int = get_relative_unix_timestamp(lfm_period)

        if relative_timestamp is None:
            relative_timestamp = 0

        NUM_ALBUMS = 9
        top_albums: list[StrippedAlbum] = get_x_top_albums(
            name, NUM_ALBUMS + 5, relative_timestamp
        )

        top_album_urls: list[str] = []
        top_album_names: list[str] = []
        index: int = 0
        while len(top_album_urls) < NUM_ALBUMS and index < len(top_albums):
            album_name = top_albums[index].album
            album_artist = top_albums[index].artist

            if (
                album_image_url := get_album_image_url(album_name, album_artist)
            ) is not None:
                top_album_urls.append(album_image_url)
                top_album_names.append(album_name)
            index += 1

        pil_img_chart: Image = combine_images(top_album_names, top_album_urls)

        with BytesIO() as image_binary:
            pil_img_chart.save(image_binary, "PNG")
            image_binary.seek(0)
            await ctx.respond(
                file=discord.File(fp=image_binary, filename=f"{user}_album_chart.png")
            )

        embed = discord.Embed(
            title=f"Album chart for {user.name if user else ctx.user.name} - {period.title()}"
        )

        # temporarily set thumbnail to get embed color the same as the first artist pic
        embed.set_thumbnail(url=top_album_urls[0])
        embed = update_embed_color(embed)
        embed.remove_thumbnail()

        await ctx.send(embed=embed)

    @has_set_lfm_user()
    @slash_command(
        name="overview",
        description="View an overview of your recent top tracks, artists, albums and genres.",
        guilds=guilds,
    )
    async def overview(
        self, ctx: ApplicationContext, user: discord.User = None
    ) -> None:
        """
        Give an overview of the user's day by day stats for their most listened to tracks, artists, albums and genres.
        """

        await ctx.defer()

        # if user supplied, set lfm_user to their last.fm username & return if they have none set
        name: str = get_lfm_username(ctx.user.id, user)
        # discord_id = ctx.user.id if user is None else user.id

        if name is None:
            await ctx.respond(
                f"{ctx.user.mention}, this user does not have a last.fm username set!"
            )
            return

        embed = discord.Embed(title="Overview of last 4 days")

        description: str = ""

        now: datetime.date = datetime.date.today()
        lower_bound: datetime.datetime = datetime.datetime(now.year, now.month, now.day)
        upper_bound: datetime.datetime = datetime.datetime.today() + datetime.timedelta(
            days=1
        )

        DAYS: int = 4
        for i in range(DAYS):

            lower_stamp = int(lower_bound.timestamp())
            upper_stamp = int(upper_bound.timestamp())

            # get top artist on day
            top_artist: StrippedArtist = None
            top_track: StrippedTrack = None
            top_album: StrippedAlbum = None
            try:
                top_artist = get_x_top_artists(name, 1, lower_stamp, upper_stamp)[0]

            except IndexError:
                # no top artist for time period, prepare for next loop
                upper_bound = lower_bound
                lower_bound = lower_bound - datetime.timedelta(days=1)
                continue

            try:
                top_track = get_x_top_tracks(name, 1, lower_stamp, upper_stamp)[0]

            except IndexError:
                print(
                    "no top track?? but there was a top artist?? should not reach this line"
                )
                continue

            top_album = get_x_top_albums(name, 1, lower_stamp, upper_stamp)[0]

            if i == 0:
                if artist_image_url := get_artist_image_url(top_artist.artist):
                    embed.set_thumbnail(url=artist_image_url)
                    embed = update_embed_color(embed)

            discord_date_timestamp = f"<t:{int(lower_bound.timestamp())}:D>"
            description += (
                f"{discord_date_timestamp}\n"
                f"`{top_artist.artist_plays}` plays - [{top_artist.artist}]({get_artist_lfm_link(top_artist.artist)})\n"
                f"`{top_album.album_plays}` plays - [{top_album.artist}]({get_artist_lfm_link(top_album.artist)}) | [{top_album.album}]({get_album_lfm_link(top_album.artist, top_album.album)})\n"
                f"`{top_track.track_plays}` plays - [{top_track.artist}]({get_artist_lfm_link(top_track.artist)}) | [{top_track.title}]({top_track.lfm_url})\n\n"
            )

            # move 1 day in the past to get the next day's info on next iteration
            upper_bound = lower_bound
            lower_bound = lower_bound - datetime.timedelta(days=1)

        if description == "":
            await ctx.respond(f"No scrobble data for past {DAYS} to use!")
            return

        # add only after checking if desc is empty to not trick it into thinking they had scrobble data
        description = (
            f"Your daily top artist, album, and track respectively.\n\n" + description
        )

        embed.description = description
        await ctx.respond(embed=embed)

    @pfp.command(
        name="update",
        description="Update the bot's profile picture to album art of your choice! Approved users only.",
    )
    @commands.cooldown(1, (60 * 10), commands.BucketType.default)
    async def pfp_change(self, ctx: ApplicationContext, album: str) -> None:
        """
        Update bot's profile picture to cover art of the given
        album, if the album is found.
        """

        await ctx.defer()

        # limit where command can be used
        approved_guilds = [938179110558105672, 315782312476409867, 108262903802511360]

        if ctx.guild_id not in approved_guilds:
            await ctx.respond(
                "You do not have permission to use this command, silly goose!"
            )
            return

        possibilities = pylast.AlbumSearch(album_name=album, network=self.network)

        try:  # if no albums found tell user
            first_result: pylast.Album = possibilities.get_next_page()[0]

        except IndexError:

            # reset cooldown if unsuccessful
            ctx.command.reset_cooldown(ctx)
            await ctx.respond(f"Unable to find album {album}!")
            return

        item_art_url = first_result.get_cover_image()
        item_art = requests.get(item_art_url).content

        try:
            await self.bot.user.edit(avatar=item_art)

        except:
            # for when discord's rate limit kicks in - shouldn't happen with the cmd cooldown
            await ctx.respond("Updated profile picture too recently! Try again soon.")
            return

        await ctx.respond(
            f"Successfully set the profile picture!\n`{first_result.get_name()} by {first_result.get_artist()}`"
        )

    async def cog_command_error(self, ctx: ApplicationContext, error: Exception):
        if isinstance(error, CheckFailure):
            await ctx.respond(
                f"{ctx.user.mention}, make sure you have set your last.fm username using `/lfm set [username]`!",
                ephemeral=True,
            )

        elif isinstance(error, CommandOnCooldown):
            # error.retry_after represents how many seconds until command can be used again
            disc_relative_timestamp: str = get_discord_relative_timestamp(
                int(error.retry_after)
            )

            await ctx.respond(
                f"{ctx.user.mention}, this command is on cooldown! Try again after {disc_relative_timestamp}.",
                ephemeral=True,
            )

        else:
            print(f"o no, error!\n{error}\n{traceback.format_exc()}")

    @commands.is_owner()
    @slash_command(name="debug")
    async def debug(self, ctx: ApplicationContext) -> None:
        """
        For debugging purposes, send recently stored scrobbles and their
        timestamps.
        """

        tracks: StrippedTrack = get_x_recent_tracks("Lego_RL", 5)

        output: str = ""

        for track in tracks:
            output += f"{track.title}: `{track.unix_timestamp}`\n"

        await ctx.respond(f"Last 5 songs:\n{output}")


def setup(bot: discord.Bot):
    bot.add_cog(LastFM(bot))


if __name__ == "__main__":
    network = pylast.LastFMNetwork(
        api_key=LFM_API_KEY,
        api_secret=LFM_API_SECRET,
    )

    me = network.get_user("Lego_RL")
    recents = me.get_recent_tracks(None, False, time_from=1661836485)
    print(recents)
