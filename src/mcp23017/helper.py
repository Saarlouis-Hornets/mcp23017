from typing import Dict, TypeVar
from collections.abc import Hashable


GenericByteT = TypeVar("GenericByteT", bound=int)


def h(v: GenericByteT) -> GenericByteT:
    """
    shorter hex call
    """
    return hex(v)

def bfp(val, size: int = 8) -> str:
    """returns a formatted version for debgging with leading 0

    :param val: the value to format
    :param size: the size of the returned string

    :return: value as 2 bit word as str 
    """
    return format(val, f'0{size}b')


def compose_all_no_subclass(cls):
    """we get all elements that are NOT
    - type instance
    - fully upper
    - start with _


    get the elements together for iteration in some of the

    :param cls:

    :return: cls

    """
    cls.all_constants = {
        key: value for key, value in cls.__dict__.items()
        if not key.startswith("_") and key.isupper() and not isinstance(value, type)
        and not callable(value)
    }
    for key, obj in cls.__dict__.items():
        if not key.startswith("_") and not isinstance(obj, type) and not callable(obj):
            if not isinstance(obj, Hashable):
                continue
            if isinstance(obj, (list, tuple)):
                for e in obj:
                    cls.all_elements_in_tuple.add(e)
            else:
                cls.all_elements_in_tuple.add(obj)
    return cls


class AllConsts:
    """
    for the IDE users...
    """
    all_constants: Dict = {}
    all_elements_in_tuple: set = set()
