#!/usr/bin/env python3

import random

from mcp23017.emulated_smbus import EmulatedSMBus
from mcp23017.i2c import I2C


def test_virtual_smbus_not_written_access():
    v_smbus = EmulatedSMBus(1, bugged=False)

    # test if they can be accessed before written to
    for i in range(100):
        assert v_smbus.read_byte(i) == 0

    for i in range(100):
        for j in range(100):
            assert v_smbus.read_byte_data(
                i, j
            ) == 0


def test_virtual_smbus_read_write():
    v_smbus = EmulatedSMBus(1, bugged=False)

    data = {}

    for i, j, k in [(random.randint(0, 500) for x in range(3)) for _ in range(1000)]:
        v_smbus.write_byte_data(i, j, k)

        # build up the state we want
        if i not in data:
            data[i] = {}

        data[i][j] = k

    # now we test and read back from smbus

    for i, ii in data.items():
        for j in ii:
            assert ii[j] == v_smbus.read_byte_data(i, j)
