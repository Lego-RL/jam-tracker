import traceback

import discord
from discord import ApplicationContext

from discord.commands import slash_command
from discord.ext import commands

from lfm import guilds


class Admin(commands.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot: discord.Bot = bot

    @commands.is_owner()
    @slash_command(name="reload", guilds=guilds)
    async def reload(self, ctx: ApplicationContext, module: str):
        try:
            self.bot.unload_extension(module)
            self.bot.load_extension(module)

        except Exception:
            await ctx.respond(traceback.format_exc())

        else:  # if module successfully reloaded
            await ctx.respond(f"Reloaded `{module}`!")


def setup(bot: discord.Bot) -> None:
    bot.add_cog(Admin(bot))
