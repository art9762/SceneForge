"""Local project execution lock; the OS releases it when its process exits."""
from __future__ import annotations

import fcntl
import os
from pathlib import Path


class ProjectBusyError(ValueError):
    """Another API or CLI execution already owns this project."""


class ProjectLock:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir.resolve()
        self._fd: int | None = None

    def acquire(self) -> ProjectLock:
        descriptor = os.open(self.project_dir / '.pipeline.lock', os.O_CREAT | os.O_RDWR
                             | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(descriptor)
            raise ProjectBusyError('Проект уже выполняется. Дождитесь текущего запуска.') from None
        except BaseException:
            os.close(descriptor)
            raise
        self._fd = descriptor
        return self

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def __enter__(self) -> ProjectLock:
        return self.acquire()

    def __exit__(self, *_):
        self.close()
