import logging
from typing import Optional

from pytest_embedded.log import DuplicateStdoutPopen, PexpectProcess


class Gdb(DuplicateStdoutPopen):
    GDB_PROG_PATH = 'xtensa-esp32-elf-gdb'
    GDB_DEFAULT_ARGS = '--nx --quiet --interpreter=mi2'

    def __init__(
        self,
        pexpect_proc: PexpectProcess,
        gdb_prog_path: Optional[str] = None,
        gdb_cli_args: Optional[str] = None,
        **kwargs,
    ):
        """
        Args:
            gdb_prog_path: gdb program path
            gdb_cli_args: gdb cli arguments
        """
        gdb_prog_path = gdb_prog_path or self.GDB_PROG_PATH
        gdb_cli_args = gdb_cli_args or self.GDB_DEFAULT_ARGS

        cmd = f'{gdb_prog_path} {gdb_cli_args}'

        logging.debug(cmd)
        super().__init__(pexpect_proc, cmd, **kwargs)

    def interpreter_exec_console(self, cmd):
        """
        GDB/MI commands -interpreter-exec console [cmd]
        """
        self.send(f'-interpreter-exec console "{cmd}"')

    def gdb_set(self, k, v):
        """
        GDB/MI commands `-gdb-set [k] [v]`
        """
        self.send(f'-gdb-set {k} {v}')

    def gdb_exit(self):
        """
        GDB/MI commands `-gdb-exit`
        """
        self.send('-gdb-exit')

    def file_exec_and_symbols(self, filepath: str):
        """
        GDB/MI commands `-file-exec-and-symbols [filepath]`
        """
        self.send(f'-file-exec-and-symbols "{filepath}"')

    def break_insert(self, location):
        """
        GDB/MI commands `-break-insert [location]`
        """
        self.send(f'-break-insert {location}')

    def exec_continue_all(self):
        """
        GDB/MI commands `-exec-continue --all`
        """
        self.send(f'-exec-continue --all')
