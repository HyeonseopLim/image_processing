"""이미지 입출력 + 증폭 실행.

- 입력: TIFF / JPEG / BMP (그레이스케일·RGB 지원)
- 선택한 기법으로 imgaug Sequential 구성 → 이미지당 N개 증폭 생성
- 출력: 입력과 동일한 확장자/모드로 저장
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import imageio.v2 as imageio
import imgaug.augmenters as iaa

from .augmenters import BY_KEY

SUPPORTED_EXTS = {".tif", ".tiff", ".jpg", ".jpeg", ".bmp"}


@dataclass
class ImageMeta:
    mode: str   # 'L'(그레이) | 'RGB' | 'RGBA'
    ext: str


# --- 입력 탐색 -----------------------------------------------------------------
def discover_images(folder: str | os.PathLike) -> list[Path]:
    """폴더 안의 지원 이미지 경로 목록(정렬)."""
    root = Path(folder)
    if not root.is_dir():
        return []
    return sorted(
        p for p in root.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS
    )


# --- 입출력 --------------------------------------------------------------------
def load_image(path: str | os.PathLike) -> tuple[np.ndarray, ImageMeta]:
    """이미지를 HxWx3 uint8 로 읽고 원본 모드 정보를 함께 반환."""
    arr = imageio.imread(path)
    ext = Path(path).suffix.lower()

    if arr.dtype != np.uint8:
        # 16bit TIFF 등 → 0~255 정규화
        a = arr.astype(np.float32)
        amin, amax = float(a.min()), float(a.max())
        a = (a - amin) / (amax - amin) * 255.0 if amax > amin else np.zeros_like(a)
        arr = a.astype(np.uint8)

    if arr.ndim == 2:
        rgb = np.repeat(arr[:, :, None], 3, axis=2)
        return rgb, ImageMeta(mode="L", ext=ext)
    if arr.ndim == 3 and arr.shape[2] == 4:
        # 알파 분리(증폭은 RGB에만 적용, 알파는 보존하지 않음 → RGB 저장)
        return np.ascontiguousarray(arr[:, :, :3]), ImageMeta(mode="RGBA", ext=ext)
    if arr.ndim == 3 and arr.shape[2] == 3:
        return np.ascontiguousarray(arr), ImageMeta(mode="RGB", ext=ext)
    # 그 외(예: 1채널 3D) → RGB 로 강제
    arr = np.atleast_3d(arr)[:, :, :1]
    return np.repeat(arr, 3, axis=2), ImageMeta(mode="L", ext=ext)


def _to_output_array(arr: np.ndarray, meta: ImageMeta) -> np.ndarray:
    """저장 직전 원본 모드에 맞게 변환."""
    if meta.mode == "L":
        # 채널 평균으로 단일 채널 복원
        return arr.mean(axis=2).round().clip(0, 255).astype(np.uint8)
    return arr


def save_image(arr: np.ndarray, path: str | os.PathLike, meta: ImageMeta) -> None:
    out = _to_output_array(arr, meta)
    ext = Path(path).suffix.lower()
    if ext in (".jpg", ".jpeg"):
        imageio.imwrite(path, out, quality=95)
    else:
        imageio.imwrite(path, out)


# --- 시퀀스 구성 ---------------------------------------------------------------
def build_sequence(selections: Iterable[tuple[str, int]]) -> iaa.Sequential:
    """selections: (기법key, 강도%) 목록 → imgaug Sequential.

    강도% 0~100 → t 0.0~1.0 로 변환해 각 기법의 build 에 전달.
    """
    augs: list[iaa.Augmenter] = []
    for key, intensity in selections:
        tech = BY_KEY.get(key)
        if tech is None:
            continue
        augs.append(tech.build(max(0, min(100, intensity)) / 100.0))
    return iaa.Sequential(augs, random_order=False)


# --- 배치 실행 -----------------------------------------------------------------
@dataclass
class BatchResult:
    total: int
    saved: int
    errors: list[tuple[str, str]]  # (파일명, 메시지)


def run_batch(
    image_paths: list[Path],
    out_dir: str | os.PathLike,
    selections: list[tuple[str, int]],
    count_per_image: int,
    progress_cb: Callable[[int, int, str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> BatchResult:
    """각 입력 이미지마다 count_per_image 개의 증폭본을 생성해 out_dir 에 저장."""
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    seq = build_sequence(selections)
    total = len(image_paths) * count_per_image
    saved = 0
    errors: list[tuple[str, str]] = []

    for path in image_paths:
        if should_stop and should_stop():
            break
        try:
            base, meta = load_image(path)
        except Exception as e:  # noqa: BLE001 - 파일 단위로 계속 진행
            errors.append((path.name, f"읽기 실패: {e}"))
            # 실패한 파일의 몫만큼 진행도 보정
            for _ in range(count_per_image):
                saved_or_skipped = saved + len(errors)
                if progress_cb:
                    progress_cb(saved_or_skipped, total, path.name)
            continue

        stem, ext = path.stem, path.suffix
        for i in range(count_per_image):
            if should_stop and should_stop():
                break
            try:
                out_arr = seq(image=base)
                out_path = out_root / f"{stem}_aug{i + 1:03d}{ext}"
                save_image(out_arr, out_path, meta)
                saved += 1
            except Exception as e:  # noqa: BLE001
                errors.append((f"{path.name}#{i+1}", str(e)))
            if progress_cb:
                progress_cb(saved + len(errors), total, path.name)

    return BatchResult(total=total, saved=saved, errors=errors)
