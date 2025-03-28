import logging
from typing import List

from .helper import compose_all_no_subclass, AllConsts
from .i2c import I2C


class MCP23017:
    @compose_all_no_subclass
    class Consts(AllConsts):
        HIGH: int = 0xFF
        LOW: int = 0x00

        INPUT: int = 0xFF
        OUTPUT: int = 0x00


        @compose_all_no_subclass
        class Register(AllConsts):
            class Index:
                A: int = 0
                B: int = 1

            IODIR:  tuple[int, int] = (0x00, 0x01)
            IPOL:  tuple[int, int] = (0x02, 0x03)
            GPINTEN:  tuple[int, int] = (0x04, 0x05)
            DEFVAL:  tuple[int, int] = (0x06, 0x07)
            INTCON:  tuple[int, int] = (0x08, 0x09)
            IOCON:  tuple[int, int] = (0x0A, 0x0B)
            GPPU:  tuple[int, int] = (0x0C, 0x0D)

            INTF:  tuple[int, int] = (0x0E, 0x0F)
            INTCAP:  tuple[int, int] = (0x10, 0x11)
            GPIO:  tuple[int, int] = (0x12, 0x13)
            OLAT:  tuple[int, int] = (0x14, 0x15)

            def get_register(self, register, index: Index):
                return getattr(self, register)[index]

        @compose_all_no_subclass
        class IO(AllConsts):
            GPA0: int = 0
            GPA1: int = 1
            GPA2: int = 2
            GPA3: int = 3
            GPA4: int = 4
            GPA5: int = 5
            GPA6: int = 6
            GPA7: int = 7
            GPB0: int = 8
            GPB1: int = 9
            GPB2: int = 10
            GPB3: int = 11
            GPB4: int = 12
            GPB5: int = 13
            GPB6: int = 14
            GPB7: int = 15

        class SettingBit:
            BANK = 7
            MIRROR = 6
            SEQOP = 5
            DISSLW = 4
            HAEN = 3
            ODR = 2
            INTPOL = 1





    def __init__(self, i2c: I2C, address, uid: str = None) -> None:
        self.i2c = i2c
        self.address = address
        self.uid = uid

    # TODO: bank for A+B reg together??


    def set_mode(self, mode, gpio) -> None:
        # mask things
        register, rel_gpio = self.get_register_gpio_tuple(self.Consts.Register.IODIR, gpio)

        self.set_bit_enabled(register, rel_gpio, True if mode is self.Consts.INPUT else False)


    def set_mode_all(self, mode) -> None:
        for reg in self.Consts.Register.IODIR:
            self.i2c.write(self.address, reg, mode)

    def get_mode(self, gpio) -> Consts:
        # TODO: implement
        logging.warning("get_mode for boards not implemented yet")
        pass

    def get_mode_all(self) -> bin:
        # HELP: what output format?
        pass



    def read(self, register):
        return self.i2c.read(self.address, register)

    def write(self, register, value):
        self.i2c.write(self.address, register, value)



    def digital_write(self, gpio, direction):
        """
        Sets the given GPIO to the given direction HIGH or LOW
        :param gpio: the GPIO to set the direction to
        :param direction: one of HIGH or LOW
        """
        # WARNING: used to write to OLAT instead of GPIO, but GPIO should cause OLAT write on the board automatically
        register, rel_gpio = self.get_register_gpio_tuple(self.Consts.Register.GPIO, gpio)
        self.set_bit_enabled(register, rel_gpio, bool(direction))



    def digital_read(self, gpio):
        """
        Reads the current direction of the given GPIO
        :param gpio: the GPIO to read from
        :return:
        """

        pair = self.get_register_gpio_tuple(self.Consts.Register.GPIO, gpio)
        bits = self.i2c.read(self.address, pair[0])
        return self.Consts.HIGH if (bits & (1 << pair[1])) > 0 else self.Consts.LOW


    def digital_read_all(self) -> List:
        return [
            self.i2c.read(self.address, register=reg) for reg in self.Consts.Register.GPIO
        ]

    def digital_write_all(self, state: bool):
        for reg in self.Consts.Register.GPIO:
            self.i2c.write(self.address, reg, self.Consts.HIGH if state else self.Consts.LOW)



    def get_register_gpio_tuple(self, registers, gpio) -> tuple:
        """
        chooses the right register and pin in that register
        :param registers:
        :param gpio:
        :return: register: int, gpio: int
        """
        # DOC: we dont really use this in prod that much soon, so that should be not that big of a slowdown
        if all(offset not in self.Consts.Register.all_elements_in_tuple for offset in registers):
            raise TypeError("registers must be valid. See description for help")
        if gpio not in self.Consts.IO.all_elements_in_tuple:
            raise TypeError("pin must be one of GPAn or GPBn. See description for help")

        register = registers[0] if gpio < 8 else registers[1]
        _gpio = gpio % 8
        return register, _gpio


    def set_bit_enabled(self, register, gpio, enable):
        state_before = self.i2c.read(self.address, register)
        value = (state_before | self.bitmask(gpio)) if enable else (state_before & ~self.bitmask(gpio))
        self.i2c.write(self.address, register, value)


    @staticmethod
    def bitmask(gpio):
        return 1 << (gpio % 8)









    def set_all_interrupt(self, enabled):
        """
        Enables or disables the interrupt of a all GPIOs
        :param enabled: enable or disable the interrupt
        """
        self.i2c.write(self.address, self.Consts.Register.GPINTEN[0], 0xFF if enabled else 0x00)
        self.i2c.write(self.address, self.Consts.Register.GPINTEN[1], 0xFF if enabled else 0x00)


    def set_interrupt_mirror(self, enable):
        """
        Enables or disables the interrupt mirroring
        :param enable: enable or disable the interrupt mirroring
        """
        self.set_bit_enabled(self.Consts.Register.IOCON[0], self.Consts.SettingBit.MIRROR, enable)
        self.set_bit_enabled(self.Consts.Register.IOCON[1], self.Consts.SettingBit.MIRROR, enable)


    def read_interrupt_captures(self):
        """
        Reads the interrupt captured register. It captures the GPIO port value at the time the interrupt occurred.
        :return: a tuple of the INTCAPA and INTCAPB interrupt capture as a list of bit string
        """
        return (
            self._get_list_of_interrupted_values_from(self.Consts.Register.INTCAP[0]),
            self._get_list_of_interrupted_values_from(self.Consts.Register.INTCAP[1])
        )


    def _get_list_of_interrupted_values_from(self, offset):
        all_int_values = []
        interrupted = self.i2c.read(self.address, offset)
        bits = '{0:08b}'.format(interrupted)
        for i in reversed(range(8)):
            all_int_values.append(bits[i])

        return all_int_values


    def read_interrupt_flags(self):
        """
        Reads the interrupt flag which reflects the interrupt condition. A set bit indicates that the associated pin caused the interrupt.
        :return: a tuple of the INTFA and INTFB interrupt flags as list of bit string
        """
        return (
            self._read_interrupt_flags_from(self.Consts.Register.INTF[0]),
            self._read_interrupt_flags_from(self.Consts.Register.INTF[1]),
        )


    def _read_interrupt_flags_from(self, offset):
        int_flags = []
        interrupted = self.i2c.read(self.address, offset)
        bits = '{0:08b}'.format(interrupted)
        for i in reversed(range(8)):
            int_flags.append(bits[i])

        return int_flags


