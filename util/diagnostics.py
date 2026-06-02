from __future__ import print_function

from contextlib import contextmanager
import inspect
from pathlib import Path
from typing import Iterator


class Diagnostics:
    """Small diagnostic output helper shared by generators and MyHDL elaboration.

    The default quiet level is intentionally chatty. Higher quiet levels suppress
    progressively more output while still leaving errors visible.
    """

    def __init__(self, quiet_level: int = 0, prefix: str = "diagnostics") -> None:
        self.quiet_level = int(quiet_level)
        self.prefix = prefix

    def info(self, message: object, quiet_level: int = 0) -> None:
        self._print(message, quiet_level)

    def detail(self, message: object) -> None:
        """Print detailed elaboration output at the most verbose level."""
        self._print(message, quiet_level=0)

    def summary(self, message: object) -> None:
        """Print high-level generator progress that survives quiet level 1."""
        self._print(message, quiet_level=1)

    def warning(self, message: object) -> None:
        """Print warnings unless the caller requested an error-only mode."""
        self._print("warning: {}".format(message), quiet_level=2)

    def error(self, message: object) -> None:
        """Print errors even at the highest quiet level."""
        self._print("error: {}".format(message), quiet_level=3)

    def with_quiet_level(self, quiet_level: int) -> "Diagnostics":
        """Return a copy with a different quiet level for temporary contexts."""
        return Diagnostics(quiet_level=quiet_level, prefix=self.prefix)

    def _print(self, message: object, quiet_level: int) -> None:
        if self.quiet_level <= quiet_level:
            print("[{}] {}".format(self._caller_module_name(), message))

    def _caller_module_name(self) -> str:
        """Resolve the module that called the public diagnostics method."""
        frame = inspect.currentframe()
        if frame is None:
            return self.prefix

        print_frame = frame.f_back
        public_method_frame = print_frame.f_back if print_frame else None
        caller_frame = public_method_frame.f_back if public_method_frame else None
        if caller_frame is None:
            return self.prefix

        module = inspect.getmodule(caller_frame)
        if module is None:
            return self.prefix

        module_name = module.__name__
        if module_name == "__main__":
            return Path(module.__file__).stem
        return module_name


_DEFAULT_DIAGNOSTICS = Diagnostics()


def get_diagnostics() -> Diagnostics:
    """Return the process-wide diagnostics object used by deep MyHDL helpers."""
    return _DEFAULT_DIAGNOSTICS


def set_diagnostics(diagnostics: Diagnostics) -> None:
    """Install a process-wide diagnostics object."""
    global _DEFAULT_DIAGNOSTICS
    _DEFAULT_DIAGNOSTICS = diagnostics


@contextmanager
def diagnostics_context(diagnostics: Diagnostics) -> Iterator[Diagnostics]:
    """Temporarily replace diagnostics and restore the previous object later."""
    previous = get_diagnostics()
    set_diagnostics(diagnostics)
    try:
        yield diagnostics
    finally:
        set_diagnostics(previous)
