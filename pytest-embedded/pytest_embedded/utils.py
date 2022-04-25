import os
from typing import AnyStr, List, Optional, TypeVar


def to_str(bytes_str: AnyStr) -> str:
    """
    Turn `bytes` or `str` to `str`

    Args:
        bytes_str: `bytes` or `str`

    Returns:
        utf8-decoded string
    """
    if isinstance(bytes_str, bytes):
        return bytes_str.decode('utf-8', errors='ignore')
    return bytes_str


def to_bytes(bytes_str: AnyStr, ending: Optional[AnyStr] = None) -> bytes:
    """
    Turn `bytes` or `str` to `bytes`

    Args:
        bytes_str: `bytes` or `str`
        ending: `bytes` or `str`, will add to the end of the result.
            Only works when the `bytes_str` is `str`

    Returns:
        utf8-encoded bytes
    """
    if isinstance(bytes_str, str):
        bytes_str = bytes_str.encode()

        if ending:
            if isinstance(ending, str):
                ending = ending.encode()
            return bytes_str + ending

    return bytes_str


_T = TypeVar('_T')


def to_list(s: _T) -> List[_T]:
    """
    Args:
        s: Anything

    Returns:
        `list(s)`. If `s` is a tuple or a set.

        itself. If `s` is a list

        `[s]`. If `s` is other types.
    """
    if not s:
        return s

    if isinstance(s, set) or isinstance(s, tuple):
        return list(s)
    elif isinstance(s, list):
        return s
    else:
        return [s]


def find_by_suffix(suffix: str, path: str) -> List[str]:
    res = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(suffix):
                res.append(os.path.join(root, file))

    return res
