#!/usr/bin/env python3

import logging
import random

from typing import List

import pytest
from mcp23017.emulated_smbus import EmulatedSMBus
from mcp23017.i2c import I2C
from mcp23017.mcp23017 import MCP23017

logging.basicConfig(
    level=1
)

try_also_bugged = True

def gen_smbusss() -> List[EmulatedSMBus]:
    busses = []

    busses.append(EmulatedSMBus(1, bugged=False))

    if try_also_bugged:
        busses.append(EmulatedSMBus(1, bugged=True))

    return busses


@pytest.mark.parametrize("v_smbus", gen_smbusss())
def test_board_digital_write_with_bugged_and_clean_smbus(v_smbus):
    i2c = I2C(v_smbus)

    board = MCP23017(i2c, 0x20)

    for io_name, gpio in board.Consts.IO.all_constants.items():
        assert board.digital_read(gpio) is False
        board.digital_write(gpio, False)
        assert board.digital_read(gpio) is False

        board.digital_write(gpio, True)
        assert board.digital_read(gpio) is True

        board.digital_write(gpio, False)

        assert board.digital_read(gpio) is False


@pytest.mark.parametrize("v_smbus", gen_smbusss())
def test_board_digital_write_all_with_bugged_and_clean(v_smbus):
    i2c = I2C(v_smbus)
    board = MCP23017(i2c, 0x21)

    all_regs_off = [0 for _ in board.Consts.Register.GPIO]

    # should be all off == 0
    assert board.digital_read_all() == all_regs_off, "test if the default is off after init"

    board.digital_write_all(False)
    assert board.digital_read_all() == all_regs_off, "should be 0 if all set to false"

    # we set everything on
    board.digital_write_all(True)
    assert board.digital_read_all() == [
        board.Consts.Register.max_value for _
        in board.Consts.Register.GPIO
    ], "test all gpio registers for their max value aka everything on"





@pytest.mark.parametrize("v_smbus", gen_smbusss())
def test_random_gpio_toggle_and_state_consistency(v_smbus):
    i2c = I2C(v_smbus)
    board = MCP23017(i2c, 0x22)

    # Ensure all are initially off
    expected_state = [0 for _ in board.Consts.Register.GPIO]
    assert board.digital_read_all() == expected_state

    all_ios = list(board.Consts.IO.all_constants.items())

    # Randomly toggle GPIOs multiple times
    for _ in range(100):
        io_name, gpio = random.choice(all_ios)
        new_state = random.choice([True, False])

        board.digital_write(gpio, new_state)

        # Update expected state manually
        reg, bit = board.get_register_gpio_tuple(
            board.Consts.Register.GPIO, gpio
        )
        reg_index = board.Consts.Register.get_index(
            board.Consts.Register.GPIO, reg
        )
        
        if new_state:
            expected_state[reg_index] |= (1 << bit)
        else:
            expected_state[reg_index] &= ~(1 << bit)

        # Verify digital_read
        assert board.digital_read(gpio) == new_state, f"{io_name} read mismatch"

        # Verify digital_read_all
        assert board.digital_read_all() == expected_state, "Mismatch after toggling GPIO"

@pytest.mark.parametrize("v_smbus", gen_smbusss())
def test_multiple_gpio_toggle_patterns(v_smbus):
    i2c = I2C(v_smbus)
    board = MCP23017(i2c, 0x23)

    all_ios = list(board.Consts.IO.all_constants.items())
    expected_state = [0 for _ in board.Consts.Register.GPIO]

    for _ in range(5):
        # Randomly choose a subset of GPIOs to toggle on
        on_ios = random.sample(all_ios, k=random.randint(1, len(all_ios)))

        for io_name, gpio in on_ios:
            board.digital_write(gpio, True)
            # Update expected state manually
            reg, bit = board.get_register_gpio_tuple(
                board.Consts.Register.GPIO, gpio
            )
            reg_index = board.Consts.Register.get_index(
                board.Consts.Register.GPIO, reg
            )

            expected_state[reg_index] |= (1 << bit)
            assert board.digital_read(gpio) is True

        assert board.digital_read_all() == expected_state, "State mismatch after setting random GPIOs ON"

        # Now turn the same ones off again
        for io_name, gpio in on_ios:
            board.digital_write(gpio, False)
            # Update expected state manually
            reg, bit = board.get_register_gpio_tuple(
                board.Consts.Register.GPIO, gpio
            )
            reg_index = board.Consts.Register.get_index(
                board.Consts.Register.GPIO, reg
            )
            
            expected_state[reg_index] &= ~(1 << bit)
            assert board.digital_read(gpio) is False

        assert board.digital_read_all() == expected_state, "State mismatch after setting GPIOs OFF"
