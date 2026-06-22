"""증폭 작업을 백그라운드 스레드에서 실행."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from ..core.pipeline import run_batch


class AugmentWorker(QThread):
    progress = Signal(int, int, str)        # done, total, 현재 파일명
    finished_ok = Signal(int, int, list)    # saved, total, errors
    failed = Signal(str)

    def __init__(self, paths: list[Path], out_dir: str,
                 selections: list[tuple[str, int]], count: int):
        super().__init__()
        self._paths = paths
        self._out_dir = out_dir
        self._selections = selections
        self._count = count
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        try:
            res = run_batch(
                self._paths, self._out_dir, self._selections, self._count,
                progress_cb=lambda d, t, n: self.progress.emit(d, t, n),
                should_stop=lambda: self._stop,
            )
            self.finished_ok.emit(res.saved, res.total, res.errors)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))
