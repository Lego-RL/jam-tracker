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

    # why does embed.thumbnail.url return string 'None'??
    if (image_url := embed.thumbnail.url) not in [None, "None"]:
        print(f"{image_url=}")
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

        if len(artist_name) < 20:
            FONT_SIZE: int = 52

        else:
            FONT_SIZE: int = 40

        font = ImageFont.truetype("Roboto-Bold.ttf", FONT_SIZE)
        text_width, text_height = draw.textsize(artist_name, font=font)

        # make black background rectangle behind text
        rectangle_size = (text_width + 20, text_height + 20)

        rectangle_img = Image.new("RGBA", rectangle_size, "black")
        rectangle_draw = ImageDraw.Draw(rectangle_img)

        # make background lower opacity
        OPACITY = 50
        paste_mask = rectangle_img.split()[3].point(lambda i: i * OPACITY // 100)

        image.paste(
            rectangle_img, ((w - rectangle_size[0]) // 2, (h - 85)), mask=paste_mask
        )
        draw.text(
            (((w - rectangle_size[0]) // 2) + 10, (h - 85)),
            artist_name,
            font=font,
        )

        updated_imgs.append(image)

    grid = Image.new("RGBA", size=(row_col_size * w, row_col_size * h))

    for i, img in enumerate(images):
        grid.paste(img, box=(i % row_col_size * w, i // row_col_size * h))
    return grid
