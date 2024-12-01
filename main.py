import asyncio
import logging
import signal
import sys

from aiotdlib import Client, ClientSettings
from config import config

from handlers import register_handlers
from helpers import load_all_messages
import tgdump

INT32_MAXLIMIT = 2**31-1

async def main():
    client = Client(
        settings=ClientSettings(
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            phone_number=config.PHONE_NUMBER,
            library_path="/Users/vladmac/Library/Caches/pypoetry/virtualenvs/python-tdlib-VZrnRyOY-py3.12/lib/python3.12/site-packages/aiotdlib/tdlib/libtdjson_darwin_arm64.dylib"
        )
    )
    register_handlers(client)

    def signal_handler(sig, frame):
        client.stop()
        tgdump.close()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    async with client:
        me = await client.api.get_me()
        logging.info(f"Successfully logged in as {me.model_dump_json()}")

        await client.api.load_chats(limit=INT32_MAXLIMIT)
        await load_all_messages(client)

        await client.idle()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
    tgdump.close()
    