from typing import Dict
from collections.abc import Hashable

def compose_all_no_subclass(cls):
    cls.all_constants = {
        key: value for key, value in cls.__dict__.items()
        if not key.startswith("_") and not isinstance(value, type)
           and not callable(value)
    }
    for key, obj in cls.__dict__.items():
        if not key.startswith("_") and not isinstance(obj, type) and not callable(obj):
            if not isinstance(obj, Hashable):
                continue
            if isinstance(obj, tuple) or isinstance(obj, list):
                for e in obj:
                    cls.all_elements_in_tuple.add(e)
            else:
                cls.all_elements_in_tuple.add(obj)
    return cls


class AllConsts:
    all_constants: Dict = {}
    all_elements_in_tuple: set = set()