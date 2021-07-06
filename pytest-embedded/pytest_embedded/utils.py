import logging
from typing import Optional, Union


class ProcessContainer:
    """
    Auto call functions under :attr:`proc_close_methods` when being garbage collected or :meth:`close`

    :ivar: proc_close_methods: A list to collect all the methods that need to be run
    """

    def __init__(self, *args, **kwargs):
        self.proc_close_methods = []
        super().__init__(*args, **kwargs)

    def __del__(self):
        self.close()

    def close(self) -> None:
        """
        Call all the sessions/threads/processes terminate methods defined in :attr:`proc_close_methods`
        """
        for func in self.proc_close_methods:
            try:
                func()
            except Exception as e:
                logging.error(e)


def to_str(bytes_str: Union[bytes, str]) -> str:
    """
    :param bytes_str: ``bytes`` or ``str``
    :return: utf8-decoded string
    """
    if isinstance(bytes_str, bytes):
        return bytes_str.decode('utf-8', errors='ignore')
    return bytes_str


def to_bytes(bytes_str: Union[bytes, str], ending: Optional[Union[bytes, str]] = None) -> bytes:
    """
    :param bytes_str: ``bytes`` or ``str``
    :param ending: ``bytes`` or ``str``, will add to the end of the result.
        Only works when the ``bytes_str`` is ``str``
    :return: utf8-encoded bytes
    """
    if isinstance(bytes_str, str):
        bytes_str = bytes_str.encode()

        if ending:
            if isinstance(ending, str):
                ending = ending.encode()
            return bytes_str + ending

    return bytes_str
