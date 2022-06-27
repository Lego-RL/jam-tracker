from io import BytesIO

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
