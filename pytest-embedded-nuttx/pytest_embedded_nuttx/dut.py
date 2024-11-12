import logging
import re
from time import sleep
from typing import AnyStr

import pexpect
from pytest_embedded_serial.dut import SerialDut

from .app import NuttxApp


class NuttxDut(SerialDut):
    """
    Generic DUT class for use with NuttX RTOS.
    """

    PROMPT_NSH = 'nsh>'
    PROMPT_TIMEOUT_S = 30

    def __init__(
        self,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

    def write(self, data: str) -> None:
        """
        Write to NuttShell and sleep for a few hundred milliseconds to
        ensure there is time for Nuttshell prompt appear again.

        Args:
            data (str): data to be passed on to Nuttshell.

        Returns:
            None.
        """
        super().write('')
        self.expect(self.PROMPT_NSH, timeout=self.PROMPT_TIMEOUT_S)
        super().write(data)
        sleep(0.25)

    def return_code(self, timeout: int = PROMPT_TIMEOUT_S) -> int:
        """
        Matches the 'echo $?' response and extracts the integer value
        corresponding to the last program return code.

        Returns:
            int: return code.
        """
        self.write('echo $?')
        echo_match = self.expect(r'echo \$\?\r\n(\d+)', timeout=timeout)
        ret_code = re.findall(r'\d+', echo_match.group().decode())

        if not ret_code:
            logging.error('Failed to retrieve return code')

        return int(ret_code[0])

    def write_and_return(self, data: str, timeout: int = 2) -> AnyStr:
        """
        Writes to Nuttshell and returns all available serial data until
        the timeout.
        This is useful when parsing and reusing the data is required, and
        pexect is not enough.

        Args:
            data (str): data to be passed on to Nuttshell.
            timeout (int): how long to wait for an answer in seconds.

        Returns:
            AnyStr
        """
        self.write(data)
        ans = self.expect(pexpect.TIMEOUT, timeout=timeout)
        return ans.rstrip().decode()


class NuttxEspDut(NuttxDut):
    """
    DUT class for serial ports connected to Espressif boards which are
    flashed with NuttX RTOS.
    """

    def __init__(
        self,
        app: NuttxApp,
        **kwargs,
    ) -> None:
        self.target = app.target

        super().__init__(app=app, **kwargs)

    def reset_to_nsh(self, ready_prompt: str = NuttxDut.PROMPT_NSH) -> None:
        """
        Resets the board and waits until the Nuttshell prompt appears.
        Defaults to 'nsh>'.

        Args:
            ready_prompt (str): string on prompt that signals completion.

        Returns:
            None
        """
        self.serial.hard_reset()
        self.expect(ready_prompt, timeout=NuttxDut.PROMPT_TIMEOUT_S)
