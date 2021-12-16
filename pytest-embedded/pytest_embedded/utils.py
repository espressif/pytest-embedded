import logging
from typing import AnyStr, Optional


class ProcessContainer:
    """
    Auto call functions under `proc_close_methods` when being garbage collected or `close()`

    Attributes:
        proc_close_methods (list[callable]): A list to collect all the methods that need to be run.
    """

    def __init__(self, *args, **kwargs):
        self.proc_close_methods = []
        super().__init__(*args, **kwargs)

    def __del__(self):
        self.close()

    def close(self) -> None:
        """
        Call all the sessions/threads/processes terminate methods defined in `proc_close_methods`
        """
        # the later it appends, the upper level it is. close the upper one first.
        for func in getattr(self, 'proc_close_methods', [])[::-1]:
            try:
                func()
            except Exception as e:
                logging.error(e)


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
