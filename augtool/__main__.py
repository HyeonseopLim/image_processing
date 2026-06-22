"""실행 진입점:  python -m augtool"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .ui.main_window import MainWindow
from .ui.style import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    family = apply_theme(app)
    win = MainWindow(family)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
