import signal
import sys
from src.config import config
import src.tgdump as tgdump

import logging
logging.basicConfig(level=logging.INFO)

from aiotdlib import Client, ClientSettings

async def main():
    client = Client(
        settings=ClientSettings(
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            phone_number=config.PHONE_NUMBER
        )
    )

    def signal_handler(sig, frame):
        client.stop()
        tgdump.close()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)