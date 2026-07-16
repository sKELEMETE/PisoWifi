import logging
import sys

# Initialize logging configuration before importing other modules
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)

from coin_serial.coin_listener import CoinListener

listener = CoinListener()
listener.run()
