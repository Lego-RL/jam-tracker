from io import BytesIO
from math import sqrt

import discord
from PIL import Image, ImageDraw, ImageFont
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

    if (image_url := embed.thumbnail.url) is not None:
        rgb: tuple = get_dominant_color(image_url)
        color = discord.Color.from_rgb(*rgb)
        embed.color = color

    # if no updates embed will return unchanged
    return embed


def combine_images(top_artist_names: list[str], image_urls: list[str]) -> Image:
    """
    Take a list of image URLs and return a combined image.
    Number of images given should always be a perfect square.
    """

    row_col_size = int(sqrt(len(image_urls)))

    images = [requests.get(url).content for url in image_urls]
    images = [Image.open(BytesIO(image)) for image in images]
    w, h = images[0].size

    updated_imgs: list = []
    # write text over every image
    for artist_name, image in zip(top_artist_names, images):
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("Roboto-Bold.ttf", 52)
        text_width, text_height = draw.textsize(artist_name, font=font)

        draw.text(
            ((w - text_width) / 2, h - 70),
            artist_name,
            font=font,
            fill=(255, 255, 255),
        )

        # draw.text((0, 0), artist_name, (255, 255, 255), font=font)
        updated_imgs.append(image)

    grid = Image.new("RGB", size=(row_col_size * w, row_col_size * h))

    for i, img in enumerate(images):
        grid.paste(img, box=(i % row_col_size * w, i // row_col_size * h))
    return grid
