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
    async def last_listened(self, ctx) -> None:
        track: list[pylast.PlayedTrack] = self.network.get_user(
            "Lego_RL"
        ).get_recent_tracks(1)

        await ctx.respond(f"Last track played was **{track[0].track.title}**.")


def setup(bot: discord.Bot):
    bot.add_cog(LastFM(bot))
