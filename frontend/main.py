from dataclasses import dataclass
from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from functools import lru_cache
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import Dict
from operator import attrgetter
from pydantic import BaseSettings
import aiofiles
import aiofiles.os as aios
import json
import re

app = FastAPI()
app.mount("/static", StaticFiles(directory="../albums"), name="static")
app.mount("/css", StaticFiles(directory="../css"), name="css")

ION_PREFIX = re.compile(r"images of note ?: ?", re.IGNORECASE)


class Settings(BaseSettings):
    albums_location: str = "../albums"


@dataclass
class AlbumPreview:
    id: str
    title: str
    datetime: int


@lru_cache
def get_settings():
    return Settings()


def templates():
    return Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(),
    )


async def get_albums_previews(settings=Depends(get_settings)):
    albums = []
    for album in await aios.listdir(settings.albums_location):
        async with aiofiles.open(
            f"{settings.albums_location}/{album}/metadata.json"
        ) as fd:
            album = AlbumPreview(**json.loads(await fd.read()))
        album.title = ION_PREFIX.sub("", album.title)
        albums.append(album)
    return sorted(albums, key=attrgetter("datetime"), reverse=True)


@app.get("/")
async def root(
    templates: Environment = Depends(templates),
    albums_previews: [AlbumPreview] = Depends(get_albums_previews),
):
    return HTMLResponse(
        templates.get_template("root.html").render({"albums": albums_previews})
    )


async def image_list_getter(settings=Depends(get_settings)):
    async def getter(album_id):
        return filter(
            lambda f: not f.endswith(".json"),
            await aios.listdir(f"{settings.albums_location}/{album_id}"),
        )

    return getter


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("favicon.ico")


@app.get("/{album_id}")
async def album(
    album_id: str,
    templates: Environment = Depends(templates),
    image_list_getter=Depends(image_list_getter),
):
    return HTMLResponse(
        templates.get_template("album.html").render(
            {
                "base_path": f"/static/{album_id}",
                "images": await image_list_getter(album_id),
            }
        )
    )
