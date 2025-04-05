"""
layer between the communication of an smbus and other code, thread safe
"""

import logging

import threading

from typing import Optional, TypeVar

from .helper import GenericByteT, h


class I2C:
    """
    simple i2c class to handle communiction between
    an smbus and other code
    """

    def __init__(self, smbus):
        """
        :param smbus:
        """
        # make it not close on exit (edit: what did i mean?)

        self.lg = logging.getLogger(self.__class__.__name__)
        self.lock = threading.Condition()

        self.smbus = smbus

    def write(self, address: GenericByteT, register: GenericByteT,
              value: GenericByteT) -> None:
        """
        write to the smbus

        """
        with self.lock:
            self.lg.hw_debug(f"wrinting {h(value)} at {h(address)}")
            self.smbus.write_byte_data(address, register, value)

    def read(self, address: GenericByteT,
             register: Optional[GenericByteT] = None):

        r = self.smbus.read_byte_data(
            address, register
        ) if register is not None else self.smbus.read_byte(address)

        self.lg.hw_debug(f"read from {h(address)} at {h(register)}: {h(r)}")
        return r
