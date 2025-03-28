from . import mcp23017, emulated_smbus
from .i2c import I2C


board_types = {
   "MCP23017": mcp23017.MCP23017
}