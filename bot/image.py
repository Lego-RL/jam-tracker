from io import BytesIO

import discord
from PIL import Image
import requests


def get_dominant_color(image_url: str):
    """
    Take a URL to an image and return the dominant color of the image.
    """

    image = requests.get(image_url)

    image = Image.open(BytesIO(image.content))
    image = image.convert("RGB")
    image = image.resize((1, 1))
    rgb = image.getpixel((0, 0))

    return rgb


def update_embed_color(embed: discord.Embed) -> discord.Embed:
    """
    Take an embed with a thumbnail set, and return the same
    embed but with its color updated to the dominant color
    in the thumbnail image.
    """

    if image_url := embed.thumbnail.url:
        rgb: tuple = get_dominant_color(image_url)
        color = discord.Color.from_rgb(*rgb)
        embed.color = color

    # if no updates embed will return unchanged
    return embed
