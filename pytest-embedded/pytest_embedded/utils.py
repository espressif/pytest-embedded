import dataclasses
import logging
import os
import re
from typing import AnyStr, Dict, List, Optional, TypeVar

from pytest_embedded import App


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
        List (list[_T]):
            - `list(s)` (List. If `s` is a tuple or a set.
            - itself. If `s` is a list.
            - `[s]`. If `s` is other types.
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


_ANSI_COLOR_CODE_RE = re.compile(
    r'''
    \x1B  # ESC
    (?:   # 7-bit C1 Fe (except CSI)
        [@-Z\\-_]
    |     # or [ for CSI, followed by a control sequence
        \[
        [0-?]*  # Parameter bytes
        [ -/]*  # Intermediate bytes
        [@-~]   # Final byte
    )
''',
    re.VERBOSE,
)


def remove_asci_color_code(s: AnyStr) -> str:
    if isinstance(s, bytes):
        s = s.decode('utf-8', errors='ignore')
    return _ANSI_COLOR_CODE_RE.sub('', s)


@dataclasses.dataclass
class Meta:
    """
    Meta info for testing, session scope
    """

    logdir: str
    port_target_cache: Dict[str, str]
    port_app_cache: Dict[str, str]
    logfile_extension: str = '.log'

    def hit_port_target_cache(self, port: str, target: str) -> bool:
        if self.port_target_cache.get(port, None) == target:
            logging.debug('hit port-target cache: %s - %s', port, target)
            return True

        return False

    def set_port_target_cache(self, port: str, target: str) -> None:
        self.port_target_cache[port] = target
        logging.debug('set port-target cache: %s - %s', port, target)

    def drop_port_target_cache(self, port: str) -> None:
        try:
            self.port_target_cache.pop(port)
            logging.debug('drop port-target cache with port %s', port)
        except KeyError:
            logging.warning('no port-target cache with port %s', port)

    def hit_port_app_cache(self, port: str, app: App) -> bool:
        if self.port_app_cache.get(port, None) == app.binary_path:
            logging.debug('hit port-app cache: %s - %s', port, app.binary_path)
            return True

        return False

    def set_port_app_cache(self, port: str, app: App) -> None:
        self.port_app_cache[port] = app.binary_path
        logging.debug('set port-app cache: %s - %s', port, app.binary_path)

    def drop_port_app_cache(self, port: str) -> None:
        try:
            self.port_app_cache.pop(port)
            logging.debug('drop port-app cache with port %s', port)
        except KeyError:
            logging.warning('no port-app cache with port %s', port)


class UserHint(Warning):
    pass
