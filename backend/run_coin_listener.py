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

import config
from coin_serial.coin_listener import CoinListener, GpioCoinListener

if config.COIN_INTERFACE == "gpio":
    listener = GpioCoinListener()
else:
    listener = CoinListener()
listener.run()
