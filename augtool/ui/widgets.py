"""기법 선택 위젯."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget,
)

from ..core.augmenters import Technique, techniques_by_category


class TechniqueRow(QWidget):
    """체크박스 + 강도 슬라이더 + 값(%) 한 줄."""

    changed = Signal()

    def __init__(self, tech: Technique, parent: QWidget | None = None):
        super().__init__(parent)
        self.tech = tech

        self.check = QCheckBox(tech.label)
        self.check.setToolTip(tech.desc)
        self.check.setMinimumWidth(120)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(tech.default_intensity)
        self.slider.setEnabled(False)
        self.slider.setToolTip(tech.desc)

        self.value_lbl = QLabel(f"{tech.default_intensity}%")
        self.value_lbl.setObjectName("Muted")
        self.value_lbl.setFixedWidth(38)
        self.value_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(10)
        lay.addWidget(self.check)
        lay.addWidget(self.slider, 1)
        lay.addWidget(self.value_lbl)

        self.check.toggled.connect(self._on_toggle)
        self.slider.valueChanged.connect(self._on_slide)

    def _on_toggle(self, on: bool) -> None:
        self.slider.setEnabled(on)
        self.changed.emit()

    def _on_slide(self, v: int) -> None:
        self.value_lbl.setText(f"{v}%")
        if self.check.isChecked():
            self.changed.emit()

    # --- 조회 ---
    def is_checked(self) -> bool:
        return self.check.isChecked()

    def intensity(self) -> int:
        return self.slider.value()

    def set_checked(self, on: bool) -> None:
        self.check.setChecked(on)


class TechniquePanel(QWidget):
    """카테고리별로 묶인 전체 기법 선택 패널."""

    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.rows: list[TechniqueRow] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        for category, techs in techniques_by_category().items():
            if not techs:
                continue
            card = QFrame()
            card.setObjectName("Card")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 12, 16, 12)
            cl.setSpacing(4)

            header = QLabel(category)
            header.setObjectName("Category")
            cl.addWidget(header)

            for tech in techs:
                row = TechniqueRow(tech)
                row.changed.connect(self.changed)
                self.rows.append(row)
                cl.addWidget(row)

            outer.addWidget(card)
        outer.addStretch(1)

    def selections(self) -> list[tuple[str, int]]:
        """체크된 기법의 (key, 강도%) 목록."""
        return [(r.tech.key, r.intensity()) for r in self.rows if r.is_checked()]

    def set_all(self, on: bool) -> None:
        for r in self.rows:
            r.check.blockSignals(True)
            r.set_checked(on)
            r.check.blockSignals(False)
            r.slider.setEnabled(on)
        self.changed.emit()
