from dataclasses import dataclass
from typing import Dict
import aiofiles
import aiofiles.os as aios
import aiohttp
import asyncio
import json
import logging
import tomllib


@dataclass
class AlbumPreview:
    id: str
    title: str
    datetime: int


@dataclass
class ImgurConfig:
    client_id: str
    account_name: str
    api_version: int


@dataclass
class StorageConfig:
    type: str
    albums_location: str


@dataclass
class Config:
    imgur: ImgurConfig
    storage: StorageConfig


async def get_newest(configuration, session):
    response = await session.get(
        f"https://api.imgur.com/{configuration.imgur.api_version}"
        f"/account/{configuration.imgur.account_name}"
        f"/submissions/0/newest?client_id={configuration.imgur.client_id}"
    )
    for album in (await response.json())["data"]:
        yield AlbumPreview(
            id=album["id"],
            title=album["title"],
            datetime=album["datetime"],
        )


async def create_metada(configuration, album_preview, base_path):
    async with aiofiles.open(f"{base_path}/metadata.json", "w") as fd:
        await fd.write(json.dumps(album_preview.__dict__))


def get_filename(image):
    return image["link"].split("/")[-1]


async def save_image(configuration, session, base_path, image):
    filename = get_filename(image)
    full_path = f"{base_path}/{filename}"
    async with session.get(image["link"]) as response:
        async with aiofiles.open(full_path, "wb") as fd:
            await fd.write(await response.read())
    print(f"\tSaved image: {filename}")


async def create_album(configuration, session, album_preview, base_path):
    await aios.mkdir(base_path)

    print(f"Creating album: {album_preview.title}")

    async with session.get(
        f"https://api.imgur.com/{configuration.imgur.api_version}"
        f"/album/{album_preview.id}/images"
        f"?client_id={configuration.imgur.client_id}"
    ) as response:
        for image in (await response.json())["data"]:
            await save_image(configuration, session, base_path, image)


async def main(configuration: Dict) -> None:
    albums = await aios.listdir(configuration.storage.albums_location)

    async with aiohttp.ClientSession(raise_for_status=True) as session:
        async for album in get_newest(configuration, session):
            base_path = f"{configuration.storage.albums_location}/{album.id}"

            if album.id in albums:
                print(f"Skipped : {album.id}")
                await create_metada(configuration, album, base_path)  # temporary
            else:
                await create_album(configuration, session, album, base_path)
                await create_metada(configuration, album, base_path)


if __name__ == "__main__":

    with open("config.toml", "rb") as f:
        raw_config = tomllib.load(f)

    imgur_config = ImgurConfig(**raw_config["imgur"])
    storage_config = StorageConfig(**raw_config["storage"])
    configuration = Config(imgur=imgur_config, storage=storage_config)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main(configuration))
