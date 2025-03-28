import random

import logging as lg
from . import logging_modes

class EmulatedSMBus:
    def __init__(self, smbus_num, bugged: bool = False):
        """
        this is a very primitive smbus emulation to let i2c modules think
        they are talking to something real
        """
        self.logger = lg.getLogger(f"EmulatedSMBus-{smbus_num}{'-bugged' if bugged else ''}")

        # this dict just has bytes stored at addresses
        self.smbus_num = smbus_num
        self._data: dict = dict()
        self._address = None
        self.bugged = bugged

        if self.bugged:
            self.logger.info(f"bugged")

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
            self.logger.hw_debug(f"current state: {[(hex(k), hex(v)) for k, v in self._data.items()]}")
            self._i = 0


        self.logger.hw_debug(f"write at {hex(register)}: {hex(value)}")
        if self.bugged:
            num_flips = min(random.choices([i for i in range(5)], weights=[0.368, 0.368, 0.184, 0.069, 0.011])[0], 8)

            mask = 0
            while bin(mask).count('1') != num_flips:
                mask = random.getrandbits(8)

            self.logger.hw_debug(f"heheehehe!!, {hex(value ^ mask)} instead of {hex(value)}")

            value = value ^ mask
            self.logger.hw_debug(f"-- writing {hex(value)} instead")


        self._data[register] = value

        self.logger.hw_debug(f"fter state: {[(hex(k), hex(v)) for k, v in self._data.items()]}")

    def read_byte(self, address: bytes) -> dict[bytes, bytes]:
        # TODO: need to fill up till some level
        self.logger.hw_debug(f"reading everything: {self._data}")
        return self._data if self._data else 0

    def read_byte_data(self, address: bytes, register: int) -> int:
        """

        :param address:
        :param register:
        :return:
        """
        self.logger.hw_debug(f"reading from {hex(register)}: {hex(self._data[register]) if register in self._data else hex(0)}")
        if register in self._data:
            return self._data[register]
        # we have to make sure we return something
        return 0


class EmulatedSMBusMCP23017(EmulatedSMBus):
      def wtf_write_byte_data(self, address: hex, register: int, value: hex) -> None:
        super().write_byte_data(address, register, value)

        o_lat = register - 2
        if o_lat in {0x12, 0x13}:
            super().write_byte_data(address, o_lat, value)
