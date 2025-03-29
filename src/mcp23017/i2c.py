import time
import logging


class I2C:
    def __init__(self, smbus, write_retries: int = 200,
                 time_between_retries_ms: int = 0,
                 invert_io: bool = False) -> None:
        """

        :param smbus:
        :param smbus_num:
        :param time_between_retries_ms: how long to wait before retrying cause some bugs
        :param write_retries: number of times to repeat the write if the result is wrong
        """
        # make it not close on exit

        # TODO: threading.Condition / LockedTracking

        self.lg = logging.getLogger(self.__class__.__name__)

        self.sbus = smbus

        self.time_between_retries_ms = time_between_retries_ms
        self.write_retries = write_retries
        self.invert_io = invert_io
        self.bit_lenght = 255

    def write(self, address: hex, register: hex, value: hex) -> None:
        if self.invert_io:
            value = self.invert(value)

        self.sbus.write_byte_data(address, register, value)

        if not self.write_retries:
            return

        try_n = 0
        good = False
        for i in range(self.write_retries):
            # HELP: what if inputs change???
            # FIXME: mask, so we dont try to change any weird stuff there??
            # TODO: put it in the board maybe??
            if self.read(address=address, register=register) == value:
                self.lg.hw_debug(f"needed {i} tries to write at {hex(address)} reg {hex(register)} {hex(value)} via bus {self.sbus}")
                good = True
                break
            else:
                if self.time_between_retries_ms:
                    time.sleep(self.time_between_retries_ms/1000)
                self.sbus.write_byte_data(address, register, value)
            try_n = i
        if not good:
            raise IOError(f"tried {try_n} times, cant write {value} at {register}, maybe the board at {address} is broken")

    def read(self, address, register=None):
        r = self.sbus.read_byte_data(
            address, register
        ) if register is not None else self.sbus.read_byte(address)
        self.lg.hw_debug(f"reading from {hex(address)} at {hex(register)}: {r:08b}")
        return self.invert(r) if self.invert_io else r


    def invert(self, v):
        if not (0 <= v <= self.bit_lenght):
            raise ValueError("bad bit, its too long. Possible other wrong inversions too")

        return ~v & self.bit_lenght
