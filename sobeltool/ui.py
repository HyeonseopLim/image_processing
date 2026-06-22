"""소벨/엣지 외곽선 강조 툴 GUI."""

from __future__ import annotations

import random
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QCheckBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QProgressBar, QPushButton, QSlider,
    QSpinBox, QVBoxLayout, QWidget,
)

from . import core as C

PREVIEW_W = 320
PREVIEW_H = 260


def np_to_pixmap(arr: np.ndarray) -> QPixmap:
    """cv2 배열(BGR 또는 gray) → QPixmap."""
    arr = np.ascontiguousarray(arr)
    if arr.ndim == 2:
        rgb = np.repeat(arr[:, :, None], 3, axis=2)
    else:
        rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
    rgb = np.ascontiguousarray(rgb)
    h, w = rgb.shape[:2]
    img = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(img.copy())


class EdgeWorker(QThread):
    progress = Signal(int, int, str)
    finished_ok = Signal(int, int, list)
    failed = Signal(str)

    def __init__(self, paths, out_dir, params):
        super().__init__()
        self._paths = paths
        self._out_dir = out_dir
        self._params = params
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            res = C.run_batch(
                self._paths, self._out_dir, self._params,
                progress_cb=lambda i, t, n: self.progress.emit(i, t, n),
                should_stop=lambda: self._stop,
            )
            self.finished_ok.emit(res.saved, res.total, res.errors)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self, font_family: str):
        super().__init__()
        self.setWindowTitle("외곽선 강조 (Sobel) 툴")
        self.resize(780, 880)

        self._images: list[Path] = []
        self._out_dir = ""
        self._base: np.ndarray | None = None
        self._base_color = False
        self._worker: EdgeWorker | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(14)

        title = QLabel("외곽선 강조 (Sobel) 툴")
        title.setObjectName("H1")
        sub = QLabel(f"폴더 안 이미지의 외곽선을 강조 · 폰트: {font_family}")
        sub.setObjectName("Muted")
        root.addWidget(title)
        root.addWidget(sub)

        root.addWidget(self._build_preview_card())
        root.addWidget(self._build_param_card())
        root.addWidget(self._build_io_card())
        root.addWidget(self._build_run_card())
        root.addStretch(1)

        self._sync_param_enabled()

    # ----------------------------------------------------------- preview
    def _build_preview_card(self) -> QFrame:
        card = QFrame(); card.setObjectName("Card")
        v = QVBoxLayout(card); v.setContentsMargins(16, 12, 16, 14); v.setSpacing(10)
        top = QHBoxLayout()
        h = QLabel("미리보기"); h.setObjectName("H2")
        self.btn_sample = QPushButton("새 샘플"); self.btn_sample.clicked.connect(self._pick_random_preview)
        top.addWidget(h); top.addStretch(1); top.addWidget(self.btn_sample)
        v.addLayout(top)

        imgs = QHBoxLayout(); imgs.setSpacing(12)
        self.lbl_orig = self._preview_label("원본")
        self.lbl_res = self._preview_label("결과")
        imgs.addLayout(self._captioned(self.lbl_orig, "원본"))
        imgs.addLayout(self._captioned(self.lbl_res, "결과"))
        v.addLayout(imgs)
        return card

    def _preview_label(self, ph: str) -> QLabel:
        lbl = QLabel(ph); lbl.setObjectName("Muted")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFixedSize(PREVIEW_W, PREVIEW_H)
        lbl.setStyleSheet("background:#FAFBFE; border:1px dashed #CBD5E1; border-radius:8px;")
        return lbl

    def _captioned(self, lbl, cap):
        box = QVBoxLayout(); box.setSpacing(4)
        box.addWidget(lbl, 0, Qt.AlignmentFlag.AlignCenter)
        c = QLabel(cap); c.setObjectName("Muted"); c.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.addWidget(c)
        return box

    # ----------------------------------------------------------- params
    def _build_param_card(self) -> QFrame:
        card = QFrame(); card.setObjectName("Card")
        g = QGridLayout(card); g.setContentsMargins(16, 14, 16, 14)
        g.setHorizontalSpacing(12); g.setVerticalSpacing(12)

        self.cmb_method = QComboBox()
        for m in C.METHODS:
            self.cmb_method.addItem(C.METHOD_LABELS[m], m)
        self.cmb_method.currentIndexChanged.connect(self._on_param_change)

        self.cmb_mode = QComboBox()
        for k, lbl in C.MODE_LABELS.items():
            self.cmb_mode.addItem(lbl, k)
        self.cmb_mode.currentIndexChanged.connect(self._on_param_change)

        self.cmb_ksize = QComboBox()
        for k in (1, 3, 5, 7):
            self.cmb_ksize.addItem(str(k), k)
        self.cmb_ksize.setCurrentIndex(1)  # 3
        self.cmb_ksize.currentIndexChanged.connect(self._on_param_change)

        self.sld_strength = QSlider(Qt.Orientation.Horizontal)
        self.sld_strength.setRange(0, 300); self.sld_strength.setValue(100)
        self.lbl_strength = QLabel("1.0"); self.lbl_strength.setObjectName("Muted")
        self.lbl_strength.setFixedWidth(34)
        self.sld_strength.valueChanged.connect(self._on_strength)
        sbox = QHBoxLayout(); sbox.addWidget(self.sld_strength, 1); sbox.addWidget(self.lbl_strength)

        self.spin_low = QSpinBox(); self.spin_low.setRange(0, 500); self.spin_low.setValue(100)
        self.spin_high = QSpinBox(); self.spin_high.setRange(0, 500); self.spin_high.setValue(200)
        self.spin_low.valueChanged.connect(self._on_param_change)
        self.spin_high.valueChanged.connect(self._on_param_change)
        cbox = QHBoxLayout()
        cbox.addWidget(QLabel("하한")); cbox.addWidget(self.spin_low)
        cbox.addWidget(QLabel("상한")); cbox.addWidget(self.spin_high); cbox.addStretch(1)

        self.chk_invert = QCheckBox("흰 배경 / 검은 선으로 반전")
        self.chk_invert.toggled.connect(self._on_param_change)

        r = 0
        g.addWidget(QLabel("엣지 방식"), r, 0); g.addWidget(self.cmb_method, r, 1); r += 1
        g.addWidget(QLabel("출력 모드"), r, 0); g.addWidget(self.cmb_mode, r, 1); r += 1
        g.addWidget(QLabel("커널 크기"), r, 0); g.addWidget(self.cmb_ksize, r, 1); r += 1
        self.lbl_strength_cap = QLabel("강도")
        g.addWidget(self.lbl_strength_cap, r, 0); g.addLayout(sbox, r, 1); r += 1
        self.lbl_canny_cap = QLabel("Canny 임계값")
        g.addWidget(self.lbl_canny_cap, r, 0); g.addLayout(cbox, r, 1); r += 1
        g.addWidget(self.chk_invert, r, 1); r += 1
        return card

    def _on_strength(self, v: int):
        self.lbl_strength.setText(f"{v/100:.1f}")
        self._on_param_change()

    def _on_param_change(self, *_):
        self._sync_param_enabled()
        self._update_preview()

    def _sync_param_enabled(self):
        method = self.cmb_method.currentData()
        mode = self.cmb_mode.currentData()
        is_canny = method == "canny"
        uses_ksize = method in ("sobel", "laplacian")
        is_enhance = mode == "enhance"

        for w in (self.lbl_strength_cap, self.sld_strength, self.lbl_strength):
            w.setEnabled(is_enhance)
        self.cmb_ksize.setEnabled(uses_ksize)
        for w in (self.lbl_canny_cap, self.spin_low, self.spin_high):
            w.setEnabled(is_canny)
        self.chk_invert.setEnabled(not is_enhance)

    def current_params(self) -> C.EdgeParams:
        return C.EdgeParams(
            method=self.cmb_method.currentData(),
            mode=self.cmb_mode.currentData(),
            ksize=self.cmb_ksize.currentData(),
            strength=self.sld_strength.value() / 100.0,
            canny_low=self.spin_low.value(),
            canny_high=self.spin_high.value(),
            invert=self.chk_invert.isChecked(),
        )

    # --------------------------------------------------------------- I/O
    def _build_io_card(self) -> QFrame:
        card = QFrame(); card.setObjectName("Card")
        g = QGridLayout(card); g.setContentsMargins(16, 14, 16, 14)
        g.setHorizontalSpacing(10); g.setVerticalSpacing(10)

        self.ed_in = QLineEdit(); self.ed_in.setReadOnly(True)
        self.ed_in.setPlaceholderText("이미지가 든 폴더")
        b_in = QPushButton("찾아보기"); b_in.clicked.connect(self._pick_input)
        self.lbl_found = QLabel("발견된 이미지: 0개"); self.lbl_found.setObjectName("Muted")
        g.addWidget(QLabel("입력 폴더"), 0, 0); g.addWidget(self.ed_in, 0, 1); g.addWidget(b_in, 0, 2)
        g.addWidget(self.lbl_found, 1, 1, 1, 2)

        self.ed_out = QLineEdit(); self.ed_out.setReadOnly(True)
        self.ed_out.setPlaceholderText("결과 저장 폴더")
        b_out = QPushButton("찾아보기"); b_out.clicked.connect(self._pick_output)
        g.addWidget(QLabel("출력 폴더"), 2, 0); g.addWidget(self.ed_out, 2, 1); g.addWidget(b_out, 2, 2)
        return card

    def _build_run_card(self) -> QFrame:
        card = QFrame(); card.setObjectName("Card")
        v = QVBoxLayout(card); v.setContentsMargins(16, 14, 16, 14); v.setSpacing(10)
        self.progress = QProgressBar(); self.progress.setValue(0)
        v.addWidget(self.progress)
        self.status = QLabel("대기 중"); self.status.setObjectName("Muted")
        v.addWidget(self.status)
        row = QHBoxLayout()
        self.btn_start = QPushButton("외곽선 변환 시작"); self.btn_start.setObjectName("Primary")
        self.btn_start.clicked.connect(self._start)
        self.btn_stop = QPushButton("중지"); self.btn_stop.setObjectName("Danger")
        self.btn_stop.setEnabled(False); self.btn_stop.clicked.connect(self._stop)
        row.addWidget(self.btn_start, 1); row.addWidget(self.btn_stop)
        v.addLayout(row)
        return card

    def _pick_input(self):
        d = QFileDialog.getExistingDirectory(self, "입력 폴더 선택")
        if not d:
            return
        self.ed_in.setText(d)
        self._images = C.discover_images(d)
        self.lbl_found.setText(f"발견된 이미지: {len(self._images)}개")
        if not self._out_dir:
            self._out_dir = str(Path(d) / "edges")
            self.ed_out.setText(self._out_dir)
        self._pick_random_preview()

    def _pick_output(self):
        d = QFileDialog.getExistingDirectory(self, "출력 폴더 선택")
        if d:
            self._out_dir = d; self.ed_out.setText(d)

    # ----------------------------------------------------------- preview
    def _pick_random_preview(self):
        if not self._images:
            return
        try:
            self._base, self._base_color = C.load_image(random.choice(self._images))
        except Exception:
            self._base = None; return
        self.lbl_orig.setPixmap(self._scaled(self._base))
        self._update_preview()

    def _update_preview(self):
        if self._base is None:
            return
        try:
            out = C.process_image(self._base, self._base_color, self.current_params())
        except Exception as e:  # noqa: BLE001
            self.status.setText(f"미리보기 오류: {e}"); return
        self.lbl_res.setPixmap(self._scaled(out))

    def _scaled(self, arr):
        return np_to_pixmap(arr).scaled(
            PREVIEW_W, PREVIEW_H,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    # --------------------------------------------------------------- run
    def _start(self):
        if not self._images:
            self.status.setText("⚠ 입력 폴더에 이미지가 없습니다."); return
        if not self._out_dir:
            self.status.setText("⚠ 출력 폴더를 선택하세요."); return
        self.btn_start.setEnabled(False); self.btn_stop.setEnabled(True)
        self.progress.setValue(0)
        self._worker = EdgeWorker(self._images, self._out_dir, self.current_params())
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _stop(self):
        if self._worker:
            self._worker.stop(); self.status.setText("중지 중…")

    def _on_progress(self, done, total, name):
        self.progress.setMaximum(total); self.progress.setValue(done)
        self.status.setText(f"처리 중… {done}/{total}  ({name})")

    def _on_finished(self, saved, total, errors):
        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False)
        msg = f"✓ 완료 — {saved}개 변환"
        if errors:
            msg += f" · 오류 {len(errors)}건"
        self.status.setText(msg); self._worker = None

    def _on_failed(self, err):
        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False)
        self.status.setText(f"✗ 실패: {err}"); self._worker = None

    def closeEvent(self, event):  # noqa: N802
        if self._worker and self._worker.isRunning():
            self._worker.stop(); self._worker.wait(2000)
        super().closeEvent(event)
