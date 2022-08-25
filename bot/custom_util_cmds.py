from email.mime import image
import discord
from discord import ApplicationContext

from discord.commands import slash_command
from discord.ext import commands

import datetime
import random

from spotify import get_artist_image_url

custom_util_guilds = [315782312476409867, 938179110558105672]


class Utils(commands.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot: discord.Bot = bot

    @slash_command(
        name="pilots",
        description="Info about albums Twenty One Pilots has released.",
        guilds=custom_util_guilds,
    )
    async def pilots(self, ctx: ApplicationContext):

        album_release_dates: dict[str, datetime.date] = {
            "Self Titled": datetime.datetime(2009, 12, 29),
            "Regional At Best": datetime.datetime(2011, 7, 8),
            "Vessel": datetime.datetime(2013, 1, 8),
            "Blurryface": datetime.datetime(2015, 5, 17),
            "Trench": datetime.datetime(2018, 10, 5),
            "Scaled And Icy": datetime.datetime(2021, 5, 21),
        }

        album_abbreviations: dict[str, str] = {
            "Self Titled": "ST",
            "Regional At Best": "RAB",
            "Vessel": "Vessel",
            "Blurryface": "BF",
            "Trench": "Trench",
            "Scaled And Icy": "SAI",
        }

        top_colors: list[str] = [
            0xF9A4CB,
            0x93D1DE,
            0xF6E518,
            0x718DBC,
            0xA75158,
            0x1E1E1E,
        ]

        embed = discord.Embed(
            color=random.choice(top_colors),
            title="Twenty One Pilots Albums",
        )
        image_url = get_artist_image_url("Twenty One Pilots")
        embed.set_thumbnail(url=image_url)

        album_names: str = ""
        album_releases: str = ""
        for album, date in album_release_dates.items():

            album_names += f"{album}\n"
            album_releases += f"<t:{round(date.timestamp())}:D>\n"

        embed.add_field(name="Albums", value=album_names, inline=True)
        embed.add_field(name="Release Dates", value=album_releases, inline=True)

        # add empty field to make 2 distinct rows
        embed.add_field(name="\u200b", value="\u200b", inline=False)

        album_period: str = ""
        amt_time_period: str = ""
        for i in range(len(album_release_dates) - 1):
            album_period += f"{album_abbreviations[list(album_release_dates)[i]]} - {album_abbreviations[list(album_release_dates)[i + 1]]}\n"
            amt_time_period += f"{(album_release_dates[list(album_release_dates)[i + 1]] - album_release_dates[list(album_release_dates)[i]]).days} days\n"

        album_period += f"SAI - Now"
        amt_time_period += f"{(datetime.datetime.now() - album_release_dates[list(album_release_dates)[-1]]).days} days"

        embed.add_field(name="Album Period", value=album_period, inline=True)
        embed.add_field(name="Amount of Time", value=amt_time_period, inline=True)

        await ctx.respond(embed=embed)


def setup(bot: discord.Bot) -> None:
    bot.add_cog(Utils(bot))
