import random

from .helper import h, GenericByteT

import logging as lg
from . import logging_modes

from typing import Dict


class EmulatedSMBus:
    """
    primitive smbus emulation to let i2c modules think
    they interacting  with something pysical
    """
    def __init__(self, smbus_num, bugged: bool = False):
        """
        :param smbus_num: we ignore that one ig
        :param bugged: let them clients work for once with some ***randomness***
 
        """
        self.logger = lg.getLogger(
            f"EmulatedSMBus-{smbus_num}{'-bugged' if bugged else ''}"
        )

        # this dict just has bytes stored at addresses
        self.smbus_num = smbus_num
        self._data: Dict[int, Dict] = {}
        self._address = None
        self.bugged = bugged

        if self.bugged:
            self.logger.info("starting in bugged mode")

        self._i = 1


    def _check_addr(self):
        """
        some wrapper

        :return:
        """
        pass

    def write_byte_data(self, address: hex, register: int, value: hex) -> None:
        """
        write to a register

        :param address: GPIO to OLAT write through
        :param register:
        :param value:

        :return:
        """
        self._i += 1
        if True or self._i > 20:
            self.logger.hw_debug(f"current state: {[(h(k), v) for k, v in self._data.items()]}")
            self._i = 0

        self.logger.hw_debug(f"write at {h(register)}: {h(value)}")
        if self.bugged:
            num_flips = min(
                random.choices(
                    list(range(5)),
                    weights=[0.368, 0.368, 0.184, 0.069, 0.011]
                )[0],
                8
            )

            mask = 0
            while bin(mask).count('1') != num_flips:
                mask = random.getrandbits(8)

            self.logger.hw_debug(f"heheehehe!!, {hex(value ^ mask)} instead of {hex(value)}")

            value = value ^ mask
            self.logger.hw_debug(f"-- writing {hex(value)} instead")

        if address not in self._data:
            self._data[address] = {}
        
        self._data[address][register] = value

        self.logger.hw_debug(f"fter state: {[(h(k), v) for k, v in self._data.items()]}")

    def read_byte(self, adr: GenericByteT) -> dict[GenericByteT, GenericByteT]:
        # TODO: need to fill up till some level (edit: what??)
        self.logger.hw_debug(f"reading everything at {adr=}: {self._data}")
        return ad if adr in self._data and (ad := self._data[adr]) else 0

    def read_byte_data(self, adr: GenericByteT, reg: int) -> int:
        """
        :param adr:
        :param reg:

        :return:
        """
        if (d_at_adr := adr in self._data) and reg in d_at_adr:
            data = d_at_adr[reg]
        # we have to make sure we return something
        else:
            data = 0
        self.logger.hw_debug(
            f"reading from adr {h(adr)} at reg {h(reg)}: {data}"
        )


class EmulatedSMBusMCP23017(EmulatedSMBus):
      def wtf_write_byte_data(self, address: hex, reg: int, value: hex) -> None:
        super().write_byte_data(address, reg, value)

        o_lat = reg - 2
        if o_lat in {0x12, 0x13}:
            super().write_byte_data(address, o_lat, value)
