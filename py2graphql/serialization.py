import enum
import math
import numbers

from .exception import InfinityNotSupportedError, UnserializableTypeError
from .types import Literal, Variable


def serialize_arg(arg):
    if isinstance(arg, bool):
        return "true" if arg else "false"
    if isinstance(arg, type(None)):
        return "null"
    elif isinstance(arg, numbers.Number):
        if math.isinf(arg):
            raise InfinityNotSupportedError(
                "Graphql doesn't support infinite floats"
            )
        return str(arg)
    elif isinstance(arg, Literal):
        return arg.name
    elif isinstance(arg, enum.Enum):
        return arg.name
    elif isinstance(arg, Variable):
        return "${}".format(arg.name)
    elif isinstance(arg, list):
        return "[{}]".format(", ".join(map(serialize_arg, arg)))
    elif isinstance(arg, dict):
        return "{{{}}}".format(
            ", ".join(
                ["{}: {}".format(k, serialize_arg(v)) for k, v in arg.items()]
            )
        )
    elif isinstance(arg, str):
        arg = (
            arg.replace("\\", "\\\\")
            .replace("\f", "\\f")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\v", "")
            .replace('"', '\\"')
        )
        return f'"{arg}"'
    else:
        raise UnserializableTypeError(arg)
