import logging

HW_DEBUG_lvl = 5

logging.addLevelName(HW_DEBUG_lvl, "HARDWARE_DEBUG")


def hw_debug(self, message, *args, **kwargs):
    if self.isEnabledFor(HW_DEBUG_lvl):
        self._log(HW_DEBUG_lvl, message, args, **kwargs)


logging.Logger.hw_debug = hw_debug
