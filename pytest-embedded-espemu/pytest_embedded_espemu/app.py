import contextlib
import logging
import os
import sys

from pytest_embedded.log import MessageQueue, live_print_call
from pytest_embedded_idf.app import IdfApp

from . import DEFAULT_IMAGE_FN


class EspEmuApp(IdfApp):
    """
    esp-emu App class

    Attributes:
        image_path (str): esp-emu flash-able bin path
    """

    def __init__(
        self,
        msg_queue: MessageQueue,
        espemu_image_path: str | None = None,
        skip_regenerate_image: bool | None = False,
        **kwargs,
    ):
        self._q = msg_queue

        super().__init__(**kwargs)

        self.image_path = espemu_image_path or os.path.join(self.binary_path, DEFAULT_IMAGE_FN)
        self.skip_regenerate_image = skip_regenerate_image

        self.create_image()

    def create_image(self) -> None:
        """
        Create the image, if it doesn't exist.
        """
        if os.path.exists(self.image_path) and self.skip_regenerate_image:
            logging.info(f'Using existing image: {self.image_path}')
            return

        try:
            import esptool  # noqa
        except ImportError:
            raise ImportError(
                'esptool is required for creating esp-emu images. '
                'Please install esptool with "pip install -U esptool" or use an existing image.'
            )

        # esp-emu accepts a plain merged flash binary, no flash-size padding needed
        with contextlib.redirect_stdout(self._q):
            live_print_call(
                [
                    sys.executable,
                    '-m',
                    'esptool',
                    '--chip',
                    self.target,
                    'merge-bin',
                    '-o',
                    self.image_path,
                    *self.write_flash_args,
                ],
                cwd=self.binary_path,
            )
