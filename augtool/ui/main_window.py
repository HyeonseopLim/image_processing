"""메인 윈도우."""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QGraphicsOpacityEffect, QGridLayout, QHBoxLayout,
    QLabel, QMainWindow, QProgressBar, QPushButton, QScrollArea, QSpinBox,
    QLineEdit, QSplitter, QVBoxLayout, QWidget,
)

from ..core import pipeline as P
from .widgets import TechniquePanel
from .worker import AugmentWorker

PREVIEW_W = 300
PREVIEW_H = 240


def np_to_pixmap(arr: np.ndarray) -> QPixmap:
    arr = np.ascontiguousarray(arr)
    if arr.ndim == 2:
        arr = np.repeat(arr[:, :, None], 3, axis=2)
    h, w = arr.shape[:2]
    img = QImage(arr.data, w, h, 3 * w, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(img.copy())


class MainWindow(QMainWindow):
    def __init__(self, font_family: str):
        super().__init__()
        self.setWindowTitle("이미지 증폭 도구 — imgaug")
        self.resize(1140, 800)

        self._images: list[Path] = []
        self._out_dir: str = ""
        self._worker: AugmentWorker | None = None
        self._preview_base: np.ndarray | None = None
        self._anim: QPropertyAnimation | None = None

        # 미리보기 디바운스 타이머
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(280)
        self._preview_timer.timeout.connect(self._update_preview)

        self._build_ui(font_family)

    # ---------------------------------------------------------------- UI
    def _build_ui(self, font_family: str) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(14)

        # 헤더
        title = QLabel("이미지 증폭 도구")
        title.setObjectName("H1")
        sub = QLabel(f"imgaug 기반 · TIFF/JPEG/BMP · 폰트: {font_family}")
        sub.setObjectName("Muted")
        head = QVBoxLayout()
        head.setSpacing(2)
        head.addWidget(title)
        head.addWidget(sub)
        root.addLayout(head)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        # --- 좌: 기법 선택 ---
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(8)

        bar = QHBoxLayout()
        lbl = QLabel("변환 기법 선택")
        lbl.setObjectName("H2")
        btn_all = QPushButton("전체 선택")
        btn_none = QPushButton("전체 해제")
        btn_all.clicked.connect(lambda: self.panel.set_all(True))
        btn_none.clicked.connect(lambda: self.panel.set_all(False))
        bar.addWidget(lbl)
        bar.addStretch(1)
        bar.addWidget(btn_all)
        bar.addWidget(btn_none)
        ll.addLayout(bar)

        self.panel = TechniquePanel()
        self.panel.changed.connect(self._schedule_preview)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.panel)
        ll.addWidget(scroll, 1)

        splitter.addWidget(left)

        # --- 우: 미리보기 + 설정 + 실행 ---
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(14)
        rl.addWidget(self._build_preview_card())
        rl.addWidget(self._build_io_card())
        rl.addWidget(self._build_run_card())
        rl.addStretch(1)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([620, 470])

    def _build_preview_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 12, 16, 14)
        v.setSpacing(10)

        top = QHBoxLayout()
        h = QLabel("미리보기")
        h.setObjectName("H2")
        self.btn_sample = QPushButton("새 샘플")
        self.btn_sample.clicked.connect(self._pick_random_preview)
        top.addWidget(h)
        top.addStretch(1)
        top.addWidget(self.btn_sample)
        v.addLayout(top)

        imgs = QHBoxLayout()
        imgs.setSpacing(12)
        self.lbl_orig = self._make_preview_label("원본")
        self.lbl_aug = self._make_preview_label("증폭 결과")
        imgs.addLayout(self._captioned(self.lbl_orig, "원본"))
        imgs.addLayout(self._captioned(self.lbl_aug, "증폭 결과"))
        v.addLayout(imgs)

        # 증폭 결과 페이드인 효과
        self._aug_effect = QGraphicsOpacityEffect(self.lbl_aug)
        self.lbl_aug.setGraphicsEffect(self._aug_effect)
        self._aug_effect.setOpacity(1.0)
        return card

    def _make_preview_label(self, placeholder: str) -> QLabel:
        lbl = QLabel(placeholder)
        lbl.setObjectName("Muted")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFixedSize(PREVIEW_W, PREVIEW_H)
        lbl.setStyleSheet(
            "background:#FAFBFE; border:1px dashed #CBD5E1; border-radius:8px;"
        )
        return lbl

    def _captioned(self, lbl: QLabel, caption: str) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(4)
        box.addWidget(lbl, 0, Qt.AlignmentFlag.AlignCenter)
        cap = QLabel(caption)
        cap.setObjectName("Muted")
        cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.addWidget(cap)
        return box

    def _build_io_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        g = QGridLayout(card)
        g.setContentsMargins(16, 14, 16, 14)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(10)

        # 입력
        self.ed_in = QLineEdit()
        self.ed_in.setReadOnly(True)
        self.ed_in.setPlaceholderText("이미지가 든 폴더를 선택하세요")
        b_in = QPushButton("찾아보기")
        b_in.clicked.connect(self._pick_input)
        self.lbl_found = QLabel("발견된 이미지: 0개")
        self.lbl_found.setObjectName("Muted")
        g.addWidget(QLabel("입력 폴더"), 0, 0)
        g.addWidget(self.ed_in, 0, 1)
        g.addWidget(b_in, 0, 2)
        g.addWidget(self.lbl_found, 1, 1, 1, 2)

        # 출력
        self.ed_out = QLineEdit()
        self.ed_out.setReadOnly(True)
        self.ed_out.setPlaceholderText("결과를 저장할 폴더")
        b_out = QPushButton("찾아보기")
        b_out.clicked.connect(self._pick_output)
        g.addWidget(QLabel("출력 폴더"), 2, 0)
        g.addWidget(self.ed_out, 2, 1)
        g.addWidget(b_out, 2, 2)

        # 증폭 개수
        self.spin = QSpinBox()
        self.spin.setRange(1, 1000)
        self.spin.setValue(10)
        self.spin.setSuffix(" 개 / 이미지")
        self.spin.valueChanged.connect(self._update_total)
        self.lbl_total = QLabel("총 생성 예정: 0개")
        self.lbl_total.setObjectName("Muted")
        g.addWidget(QLabel("증폭 개수"), 3, 0)
        g.addWidget(self.spin, 3, 1)
        g.addWidget(self.lbl_total, 4, 1, 1, 2)
        return card

    def _build_run_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(10)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        v.addWidget(self.progress)

        self.status = QLabel("대기 중")
        self.status.setObjectName("Muted")
        v.addWidget(self.status)

        row = QHBoxLayout()
        self.btn_start = QPushButton("증폭 시작")
        self.btn_start.setObjectName("Primary")
        self.btn_start.clicked.connect(self._start)
        self.btn_stop = QPushButton("중지")
        self.btn_stop.setObjectName("Danger")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop)
        row.addWidget(self.btn_start, 1)
        row.addWidget(self.btn_stop)
        v.addLayout(row)
        return card

    # ------------------------------------------------------------- 폴더
    def _pick_input(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "입력 폴더 선택")
        if not d:
            return
        self.ed_in.setText(d)
        self._images = P.discover_images(d)
        self.lbl_found.setText(f"발견된 이미지: {len(self._images)}개")
        self._update_total()
        self._preview_base = None
        if not self._out_dir:
            default_out = str(Path(d) / "augmented")
            self.ed_out.setText(default_out)
            self._out_dir = default_out
        self._pick_random_preview()

    def _pick_output(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "출력 폴더 선택")
        if d:
            self._out_dir = d
            self.ed_out.setText(d)

    def _update_total(self) -> None:
        self.lbl_total.setText(f"총 생성 예정: {len(self._images) * self.spin.value()}개")

    # ----------------------------------------------------------- 미리보기
    def _pick_random_preview(self) -> None:
        if not self._images:
            return
        path = random.choice(self._images)
        try:
            self._preview_base, _ = P.load_image(path)
        except Exception:
            self._preview_base = None
            return
        self.lbl_orig.setPixmap(self._scaled(self._preview_base))
        self._update_preview()

    def _schedule_preview(self) -> None:
        self._preview_timer.start()

    def _update_preview(self) -> None:
        if self._preview_base is None:
            return
        sels = self.panel.selections()
        try:
            if sels:
                seq = P.build_sequence(sels)
                out = seq(image=self._preview_base)
            else:
                out = self._preview_base
        except Exception as e:  # noqa: BLE001
            self.status.setText(f"미리보기 오류: {e}")
            return
        self.lbl_aug.setPixmap(self._scaled(out))
        self._fade_in()

    def _scaled(self, arr: np.ndarray) -> QPixmap:
        return np_to_pixmap(arr).scaled(
            PREVIEW_W, PREVIEW_H,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _fade_in(self) -> None:
        self._anim = QPropertyAnimation(self._aug_effect, b"opacity", self)
        self._anim.setDuration(240)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

    # --------------------------------------------------------------- 실행
    def _start(self) -> None:
        if not self._images:
            self.status.setText("⚠ 입력 폴더에 이미지가 없습니다.")
            return
        if not self._out_dir:
            self.status.setText("⚠ 출력 폴더를 선택하세요.")
            return
        sels = self.panel.selections()
        if not sels:
            self.status.setText("⚠ 변환 기법을 하나 이상 선택하세요.")
            return

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress.setValue(0)

        self._worker = AugmentWorker(self._images, self._out_dir, sels, self.spin.value())
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _stop(self) -> None:
        if self._worker:
            self._worker.stop()
            self.status.setText("중지 중…")

    def _on_progress(self, done: int, total: int, name: str) -> None:
        self.progress.setMaximum(total)
        self.progress.setValue(done)
        self.status.setText(f"처리 중… {done}/{total}  ({name})")

    def _on_finished(self, saved: int, total: int, errors: list) -> None:
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        msg = f"✓ 완료 — {saved}개 생성"
        if errors:
            msg += f" · 오류 {len(errors)}건"
        self.status.setText(msg)
        self._worker = None

    def _on_failed(self, err: str) -> None:
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status.setText(f"✗ 실패: {err}")
        self._worker = None

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(2000)
        super().closeEvent(event)
