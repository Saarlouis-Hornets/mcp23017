import logging
from typing import List, Optional, Any, Dict

import time

from .helper import compose_all_no_subclass, AllConsts
from .i2c import I2C, h, GenericByteT


class MCP23017:
    @compose_all_no_subclass
    class Consts(AllConsts):
        HIGH: int = 0xFF
        LOW: int = 0x00

        bINPUT: bool = True
        bOUTPUT: bool = False

        INPUT: int = 0xFF if bINPUT else 0x00
        OUTPUT: int = 0x00 if not bOUTPUT else 0xFF


        @compose_all_no_subclass
        class Register(AllConsts):

            bit_size: int = 8
            max_value: int = int("1"*bit_size, 2)

            class Index:
                A: int = 0
                B: int = 1

            IODIR: tuple[int, int] = (0x00, 0x01)
            IPOL: tuple[int, int] = (0x02, 0x03)
            GPINTEN: tuple[int, int] = (0x04, 0x05)
            DEFVAL: tuple[int, int] = (0x06, 0x07)
            INTCON: tuple[int, int] = (0x08, 0x09)
            IOCON: tuple[int, int] = (0x0A, 0x0B)
            GPPU: tuple[int, int] = (0x0C, 0x0D)

            INTF: tuple[int, int] = (0x0E, 0x0F)
            INTCAP: tuple[int, int] = (0x10, 0x11)
            GPIO: tuple[int, int] = (0x12, 0x13)
            OLAT: tuple[int, int] = (0x14, 0x15)

            def get_register(self, register, index: Index):
                return getattr(self, register)[index]

            def get_index(self, register_tuple: tuple[int, int],
                          register: int) -> Index:
                if register not in register_tuple:
                    raise KeyError(f"{register=} not in {register_tuple=}")
                return register_tuple.index(register)

            Mask: Dict[str, Any] = {
               "GPIO": IODIR
            }

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

    def __init__(
        self,
        i2c: I2C,
        address,
        uid: Optional[str] = None,
        invert_io: bool = False,
        check_write: bool = True,
        write_retries: int = 200,
        time_between_retries_ms: int = 10,
    ) -> None:
        self.lg = logging.getLogger(f"{__name__}.{uid}@{hex(address)}")

        self.i2c = i2c
        self.address = address
        self.uid = uid

        self.invert_io = invert_io

        self.check_write = check_write
        self.write_retries = write_retries
        self.time_between_retries_ms = time_between_retries_ms

        self.check_written: bool = False

    def set_mode(self, mode, gpio) -> None:
        # mask things
        register, rel_gpio = self.get_register_gpio_tuple(
            self.Consts.Register.IODIR, gpio
        )

        self.set_bit_enabled(
            register, rel_gpio, True if mode is self.Consts.INPUT else False
        )

    def set_mode_all(self, mode) -> None:
        for reg in self.Consts.Register.IODIR:
            self.write(reg, mode)

    def get_mode(self, gpio) -> None:
        # TODO: implement
        raise NotImplementedError("use self.get_mode_all")
        logging.warning("get_mode for boards not implemented yet")

    def get_mode_all(self) -> List[int]:
        return [
            self.read(reg) for reg in self.Consts.Register.IODIR
        ]

    def read(self, register):
        """
        read from register

        keep in mind that unconfigured pin directions and pins configured as
        input are also read there aswell as pins set as an output

        :param register: read from there

        :return:
        """
        return self.i2c.read(self.address, register)

    def write(self, reg, value,
              check_register: bool | int = True,
              desired_value: Optional[int] = None):
        """write the value to the register

        if configured, we check if the write was sucessfull and retry for
        self.write_retries times.  if still not good, return :IOError:

        :param register: register to write to
        :param value:
        :param check_register: the register to check or True to check the same
            register or False to not check at all (not recommenden)
        :param desired_value: if check_register is True and this one is given,
            we check for that instead of other stuff.  makes masking way easier

        :return:
        """

        if reg not in self.Consts.Register.GPIO:
            raise ValueError(
                f"register {h(reg)} is not a valid register to write to"
            )

        if isinstance(check_register, bool):
            check_register = reg if check_register else False

        else:
            if check_register not in self.Consts.Register.GPIO:
                raise ValueError(
                    f"register {h(check_register)} is not a valid register for checks"
                )

        self.lg.hw_debug(f"first write of {h(value)} to {h(reg)}")
        self.i2c.write(self.address, reg, value)

        number_of_tries = 0

        # in case we dont go through the retry loop i gets through the check
        good = True

        if isinstance(check_register, int) or check_register:
            for try_n in range(self.write_retries):
                # we obv have to check it again
                good = False

                # des = int(desired_value) if desired_value is not None else \
                    # value

                # get the desired value
                if (des := int(desired_value)
                    if desired_value is not None else value) \
                   == self.read(check_register):
                    self.lg.hw_debug(
                        f"needed {number_of_tries} tries to write at "
                        + f"{h(self.address)} "
                        + f"register {h(reg)}: {h(value)}. " +
                        f"checked that {h(des)} is at {check_register}"
                    )
                    good = True
                    break

                if self.time_between_retries_ms:
                    time.sleep(self.time_between_retries_ms / 1000)
                self.i2c.write(self.address, reg, value)

                number_of_tries = try_n

            if not good:
                raise IOError(
                    f"tried {number_of_tries} times, "
                    + f"can't write  {h(value)} at {h(reg)}, "
                    + f"maybe the board at {h(self.address)} is broken"
                )

    def _mask_inputs(self, v: GenericByteT, io_reg: int) -> GenericByteT:
        """
        mask out all the inputs cause we dont care about them

        :param v: value to mask
        :param io_reg: io register, we get the IO modes here

        :return: the masked value
        """
        # the register to pull to mask
        mask_register = self.Consts.Register.get_register(
            self.Consts.Register.Mask.GPIO,
            self.Consts.Register.get_index(self.Consts.Register.GPIO, io_reg),
        )
        self.lg.hw_debug(f"using as mask register for write validation: {h(mask_register)}")

        # we dont need to find out what is input and what output as its dynamic const
        mask = (r := self.read(mask_register)) if self.Consts.bINPUT \
            else invert(r, self.Consts.Register.bit_size)

        self.lg.hw_debug(f"the input mask is {h(mask)}")

        masked_v = v & mask

        self.lg.hw_debug(f"the masked value is: {h(masked_v)}")

        return masked_v

    def digital_write(self, gpio, state: bool) -> None:
        """
        Sets the given GPIO to the given direction HIGH or LOW
        :param gpio: the GPIO to set the direction to
        :param state: desired state
        """
        register, rel_gpio = self.get_register_gpio_tuple(
            self.Consts.Register.GPIO, gpio
        )
        to_write = self.set_bit_enabled(register, rel_gpio, state)
        self.write(
            register, to_write,
            desired_value=self._mask_inputs(
                to_write, register,
            )
        )

    def digital_read(self, gpio) -> bool:
        """
        Reads the current direction of the given GPIO
        :param gpio: the GPIO to read from
        :return:
        """

        pair = self.get_register_gpio_tuple(self.Consts.Register.GPIO, gpio)
        bits = self.read(pair[0])

        # FIXME tf am i returning there
        return self._invert_io(
            self.Consts.HIGH if (bits & (1 << pair[1])) > 0 else self.Consts.LOW
        )

    def digital_read_all(self) -> List[int]:
        """
        :return: list of state for each io bus
        """
        return [
            self._invert_io(self.read(reg))
            for reg in self.Consts.Register.GPIO
        ]

    def digital_write_all(self, state: bool):
        for reg in self.Consts.Register.GPIO:
            self.write(
                reg=reg,
                value=self._invert_io(self.Consts.HIGH if state else self.Consts.LOW),
                desired_value=self._mask_inputs(
                    self.read(reg),
                    reg,
                )
            )

    def get_register_gpio_tuple(self, registers, gpio) -> tuple:
        """
        chooses the right register and pin in that register
        :param registers:
        :param gpio:
        :return: register: int, gpio: int
        """
        # DOC: we dont really use this in prod that much soon, so that should be not that big of a slowdown
        if all(
            offset not in self.Consts.Register.all_elements_in_tuple
            for offset in registers
        ):
            raise TypeError(
                "registers must be valid. See description for help")
        if gpio not in self.Consts.IO.all_elements_in_tuple:
            raise TypeError(
                "pin must be one of GPAn or GPBn. See description for help")

        register = registers[0] if gpio < 8 else registers[1]
        _gpio = gpio % 8
        return register, _gpio

    def set_bit_enabled(self, reg, gpio, enable):
        state_before = self.read(reg)

        return (state_before | self.bitmask(
            gpio,
            self.Consts.Register.bit_size
        )) \
            if enable else (state_before & ~self.bitmask(
                    gpio, self.Consts.Register.bit_size
            ))

    @staticmethod
    def bitmask(gpio, bit_size: int = 8):
        return 1 << (gpio % bit_size)

    # FIXME: these might not work, they old
    def set_all_interrupt(self, enabled):
        """
        Enables or disables the interrupt of a all GPIOs
        :param enabled: enable or disable the interrupt
        """
        self.write(self.Consts.Register.GPINTEN[0], 0xFF if enabled else 0x00)
        self.write(self.Consts.Register.GPINTEN[1], 0xFF if enabled else 0x00)

    def set_interrupt_mirror(self, enable):
        """
        Enables or disables the interrupt mirroring
        :param enable: enable or disable the interrupt mirroring
        """
        self.set_bit_enabled(
            self.Consts.Register.IOCON[0], self.Consts.SettingBit.MIRROR, enable
        )
        self.set_bit_enabled(
            self.Consts.Register.IOCON[1], self.Consts.SettingBit.MIRROR, enable
        )

    def read_interrupt_captures(self):
        """
        Reads the interrupt captured register. It captures the GPIO port value at the time the interrupt occurred.
        :return: a tuple of the INTCAPA and INTCAPB interrupt capture as a list of bit string
        """
        return (
            self._get_list_of_interrupted_values_from(
                self.Consts.Register.INTCAP[0]),
            self._get_list_of_interrupted_values_from(
                self.Consts.Register.INTCAP[1]),
        )

    def _get_list_of_interrupted_values_from(self, offset):
        all_int_values = []
        interrupted = self.read(offset)
        bits = "{0:08b}".format(interrupted)
        for i in reversed(range(8)):
            all_int_values.append(bits[i])

        return all_int_values

    def read_interrupt_flags(self):
        """
        Reads the interrupt flag which reflects the interrupt condition. A set bit indicates that the associated pin caused the interrupt.
        :return: a tuple of the INTFA and INTFB interrupt flags as list of bit string
        """
        def _read_interrupt_flags(interrupted) -> List:
            int_flags = []
            bits = f"{interrupted:08b}"
            for i in reversed(range(8)):
                int_flags.append(bits[i])

                return int_flags

        return [
            _read_interrupt_flags(self.read(reg))
            for reg in self.Consts.Register.INTF
        ]

    def _invert_io(self, v: int, size: Optional[int] = None) -> int:
        """
        invert based on bus lenght

        make sure that the :size: is correct, as a wrong size might
        not be caught by checks

        """
        if self.invert_io:
            if size is None:
                size = self.bit_lenght

            if not (0 <= v <= size):
                raise ValueError(
                    f"bad bit '{hex(v)}', cant invert it "
                    + "you might want to check out all the code as its "
                    + "possible "
                    + "that values with wrong lenghts are being inverted"
                    + "without noticing"
                )

            return invert(v, size)
        return v


def invert(v: int, size: int) -> int:
    """
    invert

    :param v: value
    :param size: size of :v:
    :return: invert of :v: with size of :size:
    """
    return ~v & size
