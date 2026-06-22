"""엣지 검출 + 외곽선 강조 처리.

- 입력: TIFF / JPEG / BMP / PNG (그레이스케일·컬러)
- 엣지 방식: Sobel / Scharr / Laplacian / Canny
- 출력 모드:
    enhance   = 원본에 엣지를 덧입혀 외곽선 강조 (기본)
    edge_only = 엣지 맵만 출력
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

SUPPORTED_EXTS = {".tif", ".tiff", ".jpg", ".jpeg", ".bmp", ".png"}

METHODS = ["sobel", "scharr", "laplacian", "canny"]
METHOD_LABELS = {
    "sobel": "Sobel",
    "scharr": "Scharr (정밀)",
    "laplacian": "Laplacian",
    "canny": "Canny (윤곽선)",
}
MODE_LABELS = {"enhance": "외곽선 강조", "edge_only": "외곽선만"}


@dataclass
class EdgeParams:
    method: str = "sobel"
    mode: str = "enhance"
    ksize: int = 3            # Sobel/Laplacian 커널 크기 (1,3,5,7)
    strength: float = 1.0     # enhance 시 엣지 덧입히는 비율 (0~3)
    canny_low: int = 100
    canny_high: int = 200
    invert: bool = False      # edge_only 시 흰 배경/검은 선으로 반전


# --- 입력 탐색 -----------------------------------------------------------------
def discover_images(folder: str | os.PathLike) -> list[Path]:
    root = Path(folder)
    if not root.is_dir():
        return []
    return sorted(
        p for p in root.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS
    )


# --- 입출력 --------------------------------------------------------------------
def load_image(path: str | os.PathLike) -> tuple[np.ndarray, bool]:
    """이미지를 uint8 로 읽음. 반환: (배열, is_color)."""
    arr = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if arr is None:
        raise ValueError("이미지를 읽을 수 없습니다")

    if arr.dtype != np.uint8:  # 16bit 등 → 0~255
        a = arr.astype(np.float32)
        lo, hi = float(a.min()), float(a.max())
        arr = ((a - lo) / (hi - lo) * 255.0 if hi > lo else np.zeros_like(a)).astype(np.uint8)

    if arr.ndim == 3 and arr.shape[2] == 4:        # BGRA → BGR
        arr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
    is_color = arr.ndim == 3 and arr.shape[2] == 3
    return arr, is_color


def save_image(arr: np.ndarray, path: str | os.PathLike) -> None:
    ext = Path(path).suffix.lower()
    params = [int(cv2.IMWRITE_JPEG_QUALITY), 95] if ext in (".jpg", ".jpeg") else []
    if not cv2.imwrite(str(path), arr, params):
        raise IOError(f"저장 실패: {path}")


# --- 엣지 계산 -----------------------------------------------------------------
def _odd_ksize(k: int) -> int:
    k = max(1, min(7, int(k)))
    return k if k % 2 == 1 else k + 1


def compute_edges(gray: np.ndarray, p: EdgeParams) -> np.ndarray:
    """그레이스케일 → 0~255 엣지 맵(uint8, 단일 채널)."""
    if p.method == "canny":
        return cv2.Canny(gray, p.canny_low, p.canny_high)

    if p.method == "scharr":
        gx = cv2.Scharr(gray, cv2.CV_64F, 1, 0)
        gy = cv2.Scharr(gray, cv2.CV_64F, 0, 1)
        mag = cv2.magnitude(gx, gy)
    elif p.method == "laplacian":
        mag = np.abs(cv2.Laplacian(gray, cv2.CV_64F, ksize=_odd_ksize(p.ksize)))
    else:  # sobel
        k = _odd_ksize(p.ksize)
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=k)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=k)
        mag = cv2.magnitude(gx, gy)

    edges = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
    return edges.astype(np.uint8)


def process_image(arr: np.ndarray, is_color: bool, p: EdgeParams) -> np.ndarray:
    """단일 이미지 처리 → 출력 배열."""
    gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY) if is_color else arr
    edges = compute_edges(gray, p)

    if p.mode == "edge_only":
        out = 255 - edges if p.invert else edges
        return out

    # enhance: 원본에 엣지를 덧입혀 외곽선 강조
    if is_color:
        edges_c = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        base = arr
    else:
        edges_c = edges
        base = gray
    out = cv2.addWeighted(base, 1.0, edges_c, float(p.strength), 0)
    return out


# --- 배치 ----------------------------------------------------------------------
@dataclass
class BatchResult:
    total: int
    saved: int
    errors: list[tuple[str, str]] = field(default_factory=list)


def run_batch(
    image_paths: list[Path],
    out_dir: str | os.PathLike,
    p: EdgeParams,
    progress_cb: Callable[[int, int, str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> BatchResult:
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    total = len(image_paths)
    saved = 0
    errors: list[tuple[str, str]] = []

    for idx, path in enumerate(image_paths, 1):
        if should_stop and should_stop():
            break
        try:
            arr, is_color = load_image(path)
            out = process_image(arr, is_color, p)
            save_image(out, out_root / f"{path.stem}_edge{path.suffix}")
            saved += 1
        except Exception as e:  # noqa: BLE001 - 파일 단위 계속 진행
            errors.append((path.name, str(e)))
        if progress_cb:
            progress_cb(idx, total, path.name)

    return BatchResult(total=total, saved=saved, errors=errors)
