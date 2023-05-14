import asyncio
import tomllib

with open("secrets.toml", "rb") as f:
    secrets = tomllib.load(f)


async def load_metadata():
    return config


async def main():
    metadata = await load_metadata()
    print(metadata)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
