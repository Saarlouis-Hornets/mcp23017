import logging
from typing import List, Optional, Any, Dict

import time

from .helper import h, bfp, compose_all_no_subclass, AllConsts
from .i2c import I2C, h, GenericByteT

from . import logging_modes


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

            class _max_value_class_property:
                """some shenanigens to have a classmethod property
                """
                def __init__(self, f):
                    self.func = f

                def __get__(self, instance, owner):
                    return self.func(owner)

            @_max_value_class_property
            def max_value(cls) -> int:
                return int("1"*cls.bit_size, 2)

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

            @classmethod
            def get_register_and_index(cls, reg: int) -> tuple[str, int]:
                for reg_from_t, (low, high) in cls.all_constants.items():
                    if reg == low:
                        return (reg_from_t, 0)
                    elif reg == high:
                        return (reg_from_t, 1)
                raise ValueError(f"{h(reg)} is not a register in Consts")

            @classmethod
            def get_all_registers_and_index(cls, reg: int) -> list[tuple[str,int]]:
                # FIXME
                matches = []
                for reg, (low, high) in REGISTERS.items():
                    if index == low:
                        matches.append((reg, 0))
                    elif index == high:
                        matches.append((reg, 1))
                return matches

            @classmethod
            def get_register(cls, register_name: str, index: int) -> int:
                if not hasattr(cls, register_name):
                    raise AttributeError(f"Register '{register_name}' does not exist.")

                register_tuple = getattr(cls, register_name)

                if not isinstance(register_tuple, tuple):
                    raise TypeError(f"Register '{register_name}' is not a tuple.")

                if index not in (0, 1):
                    raise ValueError("Index must be 0 (A) or 1 (B).")

                return register_tuple[index]

            # TODO: we need get a the key of a register

            @staticmethod
            def get_register_by_tuple(
                    register_tuple: tuple[int, int],
                    register_index: int
            ) -> int:
                return register_tuple[register_index]

            @staticmethod
            def get_index(register_tuple: tuple[int, int], register: int) -> int:
                try:
                    return register_tuple.index(register)
                except ValueError as exc:
                    raise KeyError(f"{register=} not found in {register_tuple=}") from exc



                #            @classmethod
                #            def get_register(cls, register: str, index: int):
                #                return getattr(cls, register)[index]
                #
                #           @classmethod
                #          def get_index(
                #                 cls, register_tuple: tuple[int, int],
                #                register: int) -> int:
                #           if register not in register_tuple:
                #              raise KeyError(f"{register=} not in {register_tuple=}")
                #         return register_tuple.index(register)

            Mask: Dict[str, tuple[int, int]] = {
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
        auto_low: bool = True,
        check_write: bool = True,
        write_retries: int = 200,
        time_between_retries_ms: int = 10,
    ) -> None:
        """
        """
        self.lg = logging.getLogger(f"{__name__}.{uid}@{hex(address)}")

        self.i2c = i2c
        self.address = address
        self.uid = uid

        self.invert_io = invert_io

        self.check_write = check_write
        self.write_retries = write_retries
        self.time_between_retries_ms = time_between_retries_ms

        self.check_written: bool = False

    def set_gpio_mode(self, mode, gpio: int,
                      set_low: bool = True) -> None:
        """Set a gpio mode of a pin.

        :param mode:
        :param gpio:
        :param set_low: if mode is OUTPUT, set the gpio output to low.  Usefull
            with inverted boards, so that its not on when set up
        """
        # mask things
        register, rel_gpio = self.get_register_gpio_tuple(
            self.Consts.Register.IODIR, gpio
        )

        self.write(register, self.get_bit_enabled(
            register, rel_gpio, True if mode is self.Consts.INPUT else False
        ))

        if mode == self.Consts.OUTPUT and set_low:
            self.gpio_digital_write(gpio, self.Consts.LOW)



    def set_gpio_mode_all(self, mode,
                          set_all_low: bool = True) -> None:
        for reg in self.Consts.Register.IODIR:
            self.write(reg, mode)

        if mode == self.Consts.OUTPUT and set_all_low:
            self.gpio_digital_write_all(self.Consts.LOW)

    def get_gpio_mode(self, gpio: int) -> int:
        """
        get set gpio modes
        :param gpio:

        :return: the gpio mode of gpio
        """
        # TODO: implement
        logging.warning("get_mode for boards not implemented yet")
        raise NotImplementedError("use self.get_mode_all")

    def get_gpio_mode_all(self) -> List[int]:
        return [
            self.read(reg) for reg in self.Consts.Register.IODIR
        ]

    def read(self, register):
        """
        read from register

        keep in mind that reconfigured pin directions and pins configured as
        input are also read there as well as pins set as an output

        :param register: read from there

        :return:
        """
        return self.i2c.read(self.address, register)

    def write(self, reg, value,
              check_register: bool | int = True,
              desired_value: Optional[int] = None,
              check_mask: Optional[int | bool] = None,
              check_mask_register: Optional[int] = None,
              ) -> None:
        """write the value to the register

        if configured, we check if the write was successful and retry for
        self.write_retries times.  if still not good, return :IOError:

        :param reg: register to write to
        :param value: write that to :reg:
        :param check_register: the register to check for :desired_value: if
            True, check in :reg: if False skip checks
        :param desired_value: if check_register is True we check for given value
            to be in :check_register:, if not we check for :value:
        :param check_mask: TODO mask the check_register with this before
            comparing to desired_value (desired_value &~ actual)
        :param check_mask_register: if :check_mask: is true, we read that
            register and use the output as a mask


        :return:
        """

        # TODO: invert option (if for example we need to mask the inputs not the outputs)

        if reg not in self.Consts.Register.all_elements_in_tuple:
            raise ValueError(
                f"register {h(reg)} is not a valid register to write to"
            )

        if isinstance(check_register, bool):
            check_register = reg if check_register else False
        if desired_value is None:
            desired_value = value

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


                # get the desired value
                # also:
                # we dont mask anything here, cause we dont have the contex
                # that has to be done in upper functions

                # TODO: impl check_register

                actual = self.read(check_register)

                if check_mask is not None:
                    if isinstance(check_mask, bool):
                        if check_mask:
                            if check_mask_register is None:
                                raise ValueError(f"we need a mask location if {check_mask=} and no mask is provided")


                            self.lg.hw_debug(f"getting mask from {h(check_mask_register)}")
                            g_mask = self.read(check_mask_register)
                            self.lg.hw_debug(f"applying mask {h(g_mask)} to {actual=}")
                            actual = actual & ~g_mask

                    else:
                        # we just apply it then
                        self.lg.hw_debug(f"got actual value at {h(check_register)}. " +
                                         f"applying mask {h(check_mask)}")
                        actual = actual & ~check_mask
                    self.lg.hw_debug(
                        f"new actual after mask is: {h(actual)}"
                    )


                if (des := desired_value) == actual:
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
                    f"tried {number_of_tries} times, " +
                    f"can't write  {h(value)} at {h(reg)}, " +
                    f"maybe the board at {h(self.address)} is broken" +
                    f". {desired_value=}" +
                    f"\n --- its atm: {h(self.read(reg))}, chck_reg: {h(check_register)}"
                )

    def get_mask_reg(self, reg: int) -> int:
        """get the mask from the Consts corresponding with reg

        :param reg: the register we need the mask for
        :return: register to get the mask
        """
        register_name, register_index = self.Consts.Register.get_register_and_index(reg)

        #mask = self.Consts.Register.get_register(
        #    register_name=self.Consts.Register.Mask[register_name],
        #    # FIXME: is that safe? think so
        #    index=register_index
        #)
        mask = self.Consts.Register.Mask[register_name][register_index]

        return mask

    def _get_register_mask_for_io_register(self, io_reg: int) -> int:
        """get the register needed for the masking

        :param io_reg: the gpio register that we need the mask for
        :return: register to pull the mask
        """
        return self.Consts.Register.get_register_by_tuple(
            self.Consts.Register.Mask["GPIO"],
            self.Consts.Register.get_index(self.Consts.Register.GPIO, io_reg)
        )

    def _mask_inputs(self, v: GenericByteT, io_reg: int) -> GenericByteT:
        """
        mask out all the inputs cause we dont care about them

        the pins defined as output will mask the value to 0 at that
        place, no matter what the actual bit at that place is

        :param v: value to mask
        :param io_reg: io register, we get the IO modes here

        :return: the masked value
        """
        # the register to pull to mask
        mask_register = self._get_register_mask_for_io_register(io_reg)
        self.lg.hw_debug(f"using as mask register for write validation: {h(mask_register)}")

        # we dont need to find out what is input and what output as its dynamic const
        r = self.read(mask_register)
        mask = r if self.Consts.bINPUT else invert(r, self.Consts.Register.bit_size)

        self.lg.hw_debug("the input mask is: " +
                         f"{bfp(mask, self.Consts.Register.bit_size)}")

        masked_v = v & ~mask

        self.lg.hw_debug("the masked value is: " +
                         f" {bfp(masked_v), self.Consts.Register.bit_size}")

        return masked_v

    def gpio_digital_write(self, gpio, state: bool) -> None:
        """
        Sets the given GPIO to the given direction HIGH or LOW
        :param gpio: the GPIO to set the direction to
        :param state: desired state
        """

        state = self._invert_io(state, max_v=1)

        register, rel_gpio = self.get_register_gpio_tuple(
            self.Consts.Register.GPIO, gpio
        )
        to_write = self._mask_inputs(
            self.get_bit_enabled(register, rel_gpio, state),
            register
        )
        self.write(
            register, to_write,
            # FIXME: am i using the right register for masking?
            desired_value=to_write,
            check_register=True,
            check_mask=True,
            check_mask_register=self.get_mask_reg(register),
        )

    def gpio_digital_read(self, gpio) -> bool:
        """
        Reads the current direction of the given GPIO
        :param gpio: the GPIO to read from
        :return:
        """

        pair = self.get_register_gpio_tuple(self.Consts.Register.GPIO, gpio)
        bits = self.read(pair[0])

        # FIXME: im not consulting Consts.HIGH
        return bool(self._invert_io((bits & (1 << pair[1])) > 0, max_v=1))

    def gpio_digital_read_all(self) -> List[int]:
        """
        :return: list of state for each io bus
        """
        return [
            self._invert_io(self.read(reg))
            for reg in self.Consts.Register.GPIO
        ]

    def gpio_digital_write_all(self, state: bool):
        for reg in self.Consts.Register.GPIO:
            to_write = self._invert_io(self.Consts.HIGH if state else self.Consts.LOW)

            self.write(
                reg=reg,
                value=to_write,
                check_register=True,
                check_mask=True,
                check_mask_register=self.get_mask_reg(reg)
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

        bank = gpio // 8
        return registers[bank], gpio % 8

    def get_bit_enabled(self, reg, gpio, enable) -> int:
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

    def _invert_io(self, v: int, max_v: Optional[int] = None) -> int:
        """
        invert based on bus lenght

        make sure that the :max_v: is correct, as a wrong size might
        not be caught by checks

        """
        if self.invert_io:
            if max_v is None:
                max_v = self.Consts.Register.max_value

            if not (0 <= v <= max_v):
                raise ValueError(
                    f"bad bit '{hex(v)}', cant invert it "
                    + "you might want to check out all the code as its "
                    + "possible "
                    + "that values with wrong lenghts are being inverted"
                    + "without noticing"
                )

            return invert(v, max_v)
        return v


def invert(v: int, size: int) -> int:
    """
    invert

    :param v: value
    :param size: size of :v:
    :return: invert of :v: with size of :size:
    """
    return ~v & size
