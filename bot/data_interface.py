import discord

import json

import platform

up_one_file = ".." if platform.platform().lower().find("linux") > -1 else "."
data_path = up_one_file + "/data/lfm-users.json"


def store_user(discord_id: int, lfm_user: str) -> None:
    """
    Store pairing of discord user id & their associated
    last.fm account in lfm-users.json.
    """

    with open(data_path, "r") as f:
        data: dict[str, str] = json.load(f)

    data[str(discord_id)] = lfm_user

    with open(data_path, "w") as f:
        json.dump(data, f, indent=4)


def retrieve_lfm_username(discord_id: int) -> str:
    """
    Retrieve's last.fm username associated with discord
    user id.
    """

    with open(data_path, "r") as f:
        data: dict = json.load(f)

    lfm_user = data.get(str(discord_id))

    return lfm_user if lfm_user else None


def get_correct_lfm_user(invoker_id: int, user: discord.User) -> str:
    """
    Returns last.fm username of the command invoker if no user
    argument is supplied, otherwise returns last.fm username
    belonging to the discord user given.
    """

    if user:
        return retrieve_lfm_username(user.id)

    else:
        return retrieve_lfm_username(invoker_id)
