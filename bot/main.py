import discord
from dotenv import load_dotenv

import os

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
LFM_API_KEY = os.getenv("LASTFM_API_KEY")
LFM_API_SECRET = os.getenv("LASTFM_API_SECRET")
LFM_USER = os.getenv("LFM_USER")
LFM_PASS = os.getenv("LFM_PASS")
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

bot = discord.Bot()


extensions = ["lfm", "admin"]

for ext in extensions:
    bot.load_extension(ext)


@bot.event
async def on_ready():
    """
    Log the bot being properly online.
    """

    print(f"{bot.user} has connected to Discord!")


if __name__ == "__main__":
    bot.run(TOKEN)
