import json
import logging
import os

from pytest_embedded.app import App


class ArduinoApp(App):
    """
    Arduino App class

    Attributes:
        sketch (str): Sketch name.
        fqbn (str): Fully Qualified Board Name.
        target (str) : ESPxx chip.
        flash_settings (dict[str, str]): Flash settings for the target.
        binary_file (str): Merged binary file path.
        elf_file (str): ELF file path.
    """

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)

        # Extract information from binary files in the build directory
        self.binary_path = self._get_build_path()
        self.sketch = self._get_sketch_name(self.binary_path)
        self.fqbn = self._get_fqbn(self.binary_path)
        self.target = self.fqbn.split(':')[2]
        self.flash_settings = self._get_flash_settings()
        self.binary_file = os.path.realpath(os.path.join(self.binary_path, self.sketch + '.ino.merged.bin'))
        self.elf_file = os.path.realpath(os.path.join(self.binary_path, self.sketch + '.ino.elf'))

        logging.debug(f'Build path: {self.binary_path}')
        logging.debug(f'Sketch name: {self.sketch}')
        logging.debug(f'FQBN: {self.fqbn}')
        logging.debug(f'Target: {self.target}')
        logging.debug(f'Flash settings: {self.flash_settings}')
        logging.debug(f'Binary file: {self.binary_file}')
        logging.debug(f'ELF file: {self.elf_file}')

    def _get_build_path(self) -> str:
        """Infer build path from binary path or app path."""

        # Prioritize binary path over app path
        build_path = self.binary_path or self.app_path

        if not build_path:
            raise ValueError('No binary path or app path provided.')

        if os.path.isdir(build_path):
            # If build path is a directory, we need to check if it contains a .ino.bin or .ino.merged.bin file
            # If not we need to recursively check the subdirectories
            for root, dirs, files in os.walk(build_path):
                for filename in files:
                    if filename.endswith('.ino.bin') or filename.endswith('.ino.merged.bin'):
                        return root
            raise ValueError(f'Could not find a valid binary file in {build_path} or its subdirectories.')
        elif os.path.isfile(build_path) and (build_path.endswith('.ino.merged.bin') or build_path.endswith('.ino.bin')):
            # If build path is a recognized binary file, use the directory of the file
            return os.path.dirname(build_path)
        else:
            raise ValueError(f'Path {build_path} is not a directory or valid binary file.')

    def _get_sketch_name(self, build_path: str) -> str:
        """Extract sketch name from binary files in the build directory."""
        if not build_path or not os.path.isdir(build_path):
            logging.warning('No build path found. Using default sketch name "sketch".')
            return 'sketch'

        # Look for .ino.bin or .ino.merged.bin files
        for filename in os.listdir(build_path):
            if filename.endswith('.ino.bin') or filename.endswith('.ino.merged.bin'):
                # Extract sketch name (everything before .ino.bin or .ino.merged.bin)
                if filename.endswith('.ino.merged.bin'):
                    return filename[: -len('.ino.merged.bin')]
                else:
                    return filename[: -len('.ino.bin')]

        # If no .ino.bin or .ino.merged.bin files found, raise an error
        raise ValueError(f'No .ino.bin or .ino.merged.bin file found in {build_path}')

    def _get_fqbn(self, build_path: str) -> str:
        """Get FQBN from build.options.json file."""
        options_file = os.path.realpath(os.path.join(build_path, 'build.options.json'))
        with open(options_file) as f:
            options = json.load(f)
        fqbn = options['fqbn']
        return fqbn

    def _get_flash_settings(self) -> dict[str, str]:
        """Get flash settings from flash_args file."""
        flash_args_file = os.path.realpath(os.path.join(self.binary_path, 'flash_args'))
        with open(flash_args_file) as f:
            flash_args = f.readline().split(' ')

        flash_settings = {}
        for i, arg in enumerate(flash_args):
            if arg.startswith('--'):
                flash_settings[arg[2:].strip()] = flash_args[i + 1].strip()

        if flash_settings == {}:
            raise ValueError(f'Flash settings not found in {flash_args_file}')

        return flash_settings
