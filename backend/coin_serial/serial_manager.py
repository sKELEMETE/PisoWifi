import time

import serial

import config

from coin_serial.device_detector import detect_serial_device
from coin_serial.serial_reader import SerialReader


class SerialManager:
    def __init__(self):
        self.reader = None
        self.connected = False

    def is_connected(self):
        return self.connected

    def set_connected(self, value: bool):
        self.connected = value

    def connect(self):
        while self.reader is None:
            try:
                device = detect_serial_device()

                if device is None:
                    self.set_connected(False)
                    print("Coin device not found.")
                    time.sleep(config.SERIAL_RECONNECT_INTERVAL)
                    continue

                config.SERIAL_PORT = device

                self.reader = SerialReader()

                self.set_connected(True)
                print("[Serial] Connected.")
                print(f"Connected to {device}")

            except serial.SerialException:
                self.set_connected(False)
                print("Waiting for coin acceptor...")
                time.sleep(config.SERIAL_RECONNECT_INTERVAL)

    def read(self):
        if self.reader is None:
            return None

        try:
            return self.reader.read_line()

        except serial.SerialException:
            self.set_connected(False)
            print("[Serial] Device disconnected.")

            self.reader = None

            self.connect()

            return None
