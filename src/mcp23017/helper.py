from typing import Dict, TypeVar
from collections.abc import Hashable


GenericByteT = TypeVar("GenericByteT", bound=int)


def h(v: GenericByteT) -> GenericByteT:
    """
    shorter hex call
    """
    return hex(v)


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
