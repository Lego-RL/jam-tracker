import traceback

import discord
import discord.commands
from discord import ApplicationContext
from discord.commands import slash_command, SlashCommandGroup, option
from discord.ext import commands

from discord import CheckFailure
from discord.ext.commands.errors import CommandOnCooldown

import pylast
import requests

from data_interface import (
    store_user,
    retrieve_lfm_username,
    get_lfm_username,
    get_lfm_username_update_data,
    get_number_user_scrobbles_stored,
)
from image import combine_images, update_embed_color
from io import BytesIO
from main import LFM_API_KEY, LFM_API_SECRET
from spotify import get_artist_image_url, get_track_image_url
from PIL import Image

from cmd_data_helpers import StrippedTrack, StrippedArtist
from cmd_data_helpers import (
    get_x_recent_tracks,
    get_x_top_tracks,
    get_x_top_artists,
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

        name: str = get_lfm_username_update_data(self.network, ctx.user.id, user)

        if name is None:
            await ctx.respond(
                f"{ctx.user.mention}, this user does not have a last.fm username set!"
            )
            return

        num_scrobbles = get_number_user_scrobbles_stored(ctx.user.id)

        await ctx.respond(f"{name} has **{num_scrobbles}** total scrobbles!")

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
        name: str = get_lfm_username_update_data(self.network, ctx.user.id, user)

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

    # @has_set_lfm_user()
    # @slash_command(name="discover")
    # async def discover_new_from_favs(
    #     self,
    #     ctx: ApplicationContext,
    #     user: discord.User = None,
    #     include_remixes: bool = False,
    # ) -> None:
    #     """
    #     Displays songs from your favorite artists that the user
    #     has never scrobbled before.
    #     """

    #     await ctx.defer()

    #     # if user supplied, set lfm_user to their last.fm username & return if they have none set
    #     name: str = get_lfm_username(ctx.user.id, user)

    #     if name is None:
    #         await ctx.respond(
    #             f"{ctx.user.mention}, this user does not have a last.fm username set!"
    #         )
    #         return

    #     user = self.network.get_user(name)

    #     fav_artists: list[pylast.Artist] = user.get_top_artists(
    #         period=pylast.PERIOD_3MONTHS, limit=3
    #     )

    #     to_suggest: list[pylast.Track] = []

    #     for artist, _ in fav_artists:
    #         songs: list[tuple(pylast.Track, int)] = artist.get_top_tracks(limit=100)
    #         songs.reverse()  # search through least listened tracks first

    #         for song, _ in songs:

    #             if "video" in str(song).lower():
    #                 continue

    #             if not include_remixes and "remix" in str(song).lower():
    #                 continue

    #             if song.get_userplaycount() == 0:
    #                 to_suggest.append(song)
    #                 break

    #     songs_str = ""
    #     for i, song in enumerate(to_suggest):
    #         songs_str += (
    #             f"\n{i+1}) [{song.get_name()}]({song.get_url()}) - {song.get_artist()}"
    #         )

    #     embed = discord.Embed(
    #         title=f"Listening suggestions for your top artists!",
    #         color=discord.Color.gold(),
    #         description=songs_str,
    #     )

    #     embed.set_thumbnail(url=ctx.user.avatar.url)

    #     await ctx.respond(embed=embed)

    @lfm.command(
        name="set", description="Set last.fm username to use for all last.fm commands."
    )
    async def lfm_user_set(self, ctx: ApplicationContext, lfm_user: str) -> None:
        """
        Gets discord user's last.fm username to store for use with all
        last.fm related commands.
        """

        await ctx.defer()

        user: pylast.User = self.network.get_user(lfm_user)

        try:
            user.get_recent_tracks(limit=1)

        except:
            await ctx.respond(
                "Unable to fetch last.fm profile. Did you misspell your account name?"
            )
            return

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
        name: str = get_lfm_username_update_data(self.network, ctx.user.id, user)
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

            artist_link = (
                f"https://www.last.fm/music/{'+'.join(artist.artist.split(' '))}"
            )
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
        name: str = get_lfm_username_update_data(self.network, ctx.user.id, user)
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
        name: str = get_lfm_username_update_data(self.network, ctx.user.id)
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
            track_plays: int = track_data[1]
            image_url: str = track_data[2]

        except IndexError:
            await ctx.respond("Unable to find track!")
            return

        user: pylast.User = self.network.get_user(name)

        embed = discord.Embed(
            color=discord.Color.gold(),
            # description=track_info.description,
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
    @chart.command(name="artist", description="View a chart of your top artists. ")
    @option(
        name="period",
        type=str,
        description="Decides the period of time to find your top tracks for",
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
        name: str = get_lfm_username_update_data(self.network, ctx.user.id, user)
        discord_id = ctx.user.id if user is None else user.id

        if name is None:
            await ctx.respond(
                f"{ctx.user.mention}, this user does not have a last.fm username set!"
            )
            return

        lfm_period = PERIODS[period]
        relative_timestamp: int = get_relative_unix_timestamp(lfm_period)

        NUM_ARTISTS = 9
        top_artists: list[StrippedArtist] = get_x_top_artists(
            name, NUM_ARTISTS + 5, relative_timestamp
        )

        top_artist_urls: list[str] = []
        index: int = 0
        while len(top_artist_urls) < NUM_ARTISTS and index < len(top_artists):
            if (
                artist_image_url := get_artist_image_url(top_artists[index].artist)
            ) is not None:
                top_artist_urls.append(artist_image_url)
            index += 1

        pil_img_chart: Image = combine_images(top_artist_urls)

        with BytesIO() as image_binary:
            pil_img_chart.save(image_binary, "PNG")
            image_binary.seek(0)
            await ctx.respond(
                file=discord.File(fp=image_binary, filename=f"{user}_artist_chart.png")
            )

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
                f"{ctx.user.mention}, make sure you have set your last.fm username using `/lfm set [username]`!"
            )

        elif isinstance(error, CommandOnCooldown):
            # error.retry_after represents how many seconds until command can be used again
            disc_relative_timestamp: str = get_discord_relative_timestamp(
                int(error.retry_after)
            )

            await ctx.respond(
                f"{ctx.user.mention}, this command is on cooldown! Try again after {disc_relative_timestamp}."
            )

        else:
            print(f"o no, error!\n{error}\n{traceback.format_exc()}")


def setup(bot: discord.Bot):
    bot.add_cog(LastFM(bot))
