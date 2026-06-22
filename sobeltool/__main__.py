"""실행 진입점:  python -m sobeltool"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from augtool.ui.style import apply_theme  # 증폭 툴과 동일 테마 재사용
from .ui import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    family = apply_theme(app)
    win = MainWindow(family)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
