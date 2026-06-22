"""변환 기법 레지스트리.

각 기법은 강도 t(0.0~1.0)를 받아 imgaug Augmenter 를 반환하는 build 함수를 가진다.
강도 슬라이더 값(0~100%) → t = value/100 으로 전달된다.

flip 계열처럼 강도가 '확률'로 해석되는 경우 build 안에서 그렇게 매핑한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import imgaug.augmenters as iaa


@dataclass(frozen=True)
class Technique:
    key: str
    label: str                       # UI 표시명(한글)
    category: str
    build: Callable[[float], iaa.Augmenter]
    default_intensity: int = 50      # 슬라이더 기본값 (%)
    needs_rgb: bool = False          # 컬러 3채널 필요 여부 (날씨 계열 등)
    desc: str = ""


# 카테고리 표시 순서
CATEGORIES = ["기하학 변환", "밝기·색상", "노이즈·블러", "기타 (왜곡·날씨)"]


def _lerp(lo: float, hi: float, t: float) -> float:
    return lo + (hi - lo) * t


# --- 레지스트리 ----------------------------------------------------------------
TECHNIQUES: list[Technique] = [
    # === 기하학 변환 =========================================================
    Technique(
        "rotate", "회전", "기하학 변환",
        lambda t: iaa.Affine(rotate=(-_lerp(0, 45, t), _lerp(0, 45, t)), mode="reflect"),
        desc="±각도 범위 내 무작위 회전",
    ),
    Technique(
        "fliplr", "좌우 반전", "기하학 변환",
        lambda t: iaa.Fliplr(t),  # 강도 = 반전 확률
        default_intensity=50,
        desc="강도 = 좌우 반전될 확률",
    ),
    Technique(
        "flipud", "상하 반전", "기하학 변환",
        lambda t: iaa.Flipud(t),
        default_intensity=30,
        desc="강도 = 상하 반전될 확률",
    ),
    Technique(
        "translate", "이동", "기하학 변환",
        lambda t: iaa.Affine(
            translate_percent={"x": (-_lerp(0, 0.2, t), _lerp(0, 0.2, t)),
                               "y": (-_lerp(0, 0.2, t), _lerp(0, 0.2, t))},
            mode="reflect"),
        desc="가로·세로 무작위 평행이동",
    ),
    Technique(
        "scale", "확대·축소", "기하학 변환",
        lambda t: iaa.Affine(scale=(_lerp(1.0, 0.7, t), _lerp(1.0, 1.3, t)), mode="reflect"),
        desc="무작위 배율 조정",
    ),
    Technique(
        "shear", "전단(shear)", "기하학 변환",
        lambda t: iaa.Affine(shear=(-_lerp(0, 16, t), _lerp(0, 16, t)), mode="reflect"),
        desc="기울임 변형",
    ),
    Technique(
        "perspective", "원근 변형", "기하학 변환",
        lambda t: iaa.PerspectiveTransform(scale=(0.01, max(0.02, _lerp(0.02, 0.15, t)))),
        default_intensity=30,
        desc="원근 왜곡",
    ),

    # === 밝기·색상 ===========================================================
    Technique(
        "brightness", "밝기", "밝기·색상",
        lambda t: iaa.MultiplyBrightness((_lerp(1.0, 0.6, t), _lerp(1.0, 1.4, t))),
        desc="밝기 배율 조정",
    ),
    Technique(
        "contrast", "대비", "밝기·색상",
        lambda t: iaa.LinearContrast((_lerp(1.0, 0.5, t), _lerp(1.0, 1.6, t))),
        desc="명암 대비 조정",
    ),
    Technique(
        "gamma", "감마", "밝기·색상",
        lambda t: iaa.GammaContrast((_lerp(1.0, 0.5, t), _lerp(1.0, 1.8, t))),
        desc="감마 보정",
    ),
    Technique(
        "saturation", "채도", "밝기·색상",
        lambda t: iaa.MultiplySaturation((_lerp(1.0, 0.5, t), _lerp(1.0, 1.5, t))),
        needs_rgb=True,
        desc="채도 조정 (컬러 전용)",
    ),
    Technique(
        "hue", "색조(Hue)", "밝기·색상",
        lambda t: iaa.AddToHue((int(-_lerp(0, 30, t)), int(_lerp(0, 30, t)))),
        needs_rgb=True,
        default_intensity=30,
        desc="색조 이동 (컬러 전용)",
    ),
    Technique(
        "grayscale", "그레이스케일", "밝기·색상",
        lambda t: iaa.Grayscale(alpha=(0.0, t)),
        needs_rgb=True,
        default_intensity=100,
        desc="흑백화 정도 (컬러 전용)",
    ),

    # === 노이즈·블러 =========================================================
    Technique(
        "gauss_noise", "가우시안 노이즈", "노이즈·블러",
        lambda t: iaa.AdditiveGaussianNoise(scale=(0, _lerp(0, 0.12, t) * 255)),
        desc="픽셀 단위 가우시안 잡음",
    ),
    Technique(
        "gauss_blur", "가우시안 블러", "노이즈·블러",
        lambda t: iaa.GaussianBlur(sigma=(0, _lerp(0, 3.0, t))),
        desc="흐림 효과",
    ),
    Technique(
        "motion_blur", "모션 블러", "노이즈·블러",
        lambda t: iaa.MotionBlur(k=int(round(_lerp(3, 15, t))) | 1),  # 홀수 보장
        default_intensity=30,
        desc="움직임 흐림",
    ),
    Technique(
        "dropout", "드롭아웃", "노이즈·블러",
        lambda t: iaa.Dropout(p=(0, max(0.001, _lerp(0, 0.1, t)))),
        default_intensity=30,
        desc="픽셀 무작위 제거(0으로)",
    ),
    Technique(
        "salt_pepper", "소금·후추 노이즈", "노이즈·블러",
        lambda t: iaa.SaltAndPepper(p=(0, max(0.001, _lerp(0, 0.1, t)))),
        default_intensity=30,
        desc="흑백 점 잡음",
    ),

    # === 기타 (왜곡·날씨) ====================================================
    Technique(
        "sharpen", "선명화(Sharpen)", "기타 (왜곡·날씨)",
        lambda t: iaa.Sharpen(alpha=(0.0, t), lightness=(0.8, 1.2)),
        default_intensity=40,
        desc="윤곽 강조",
    ),
    Technique(
        "elastic", "탄성 변형", "기타 (왜곡·날씨)",
        lambda t: iaa.ElasticTransformation(alpha=(0, _lerp(0, 40, t)), sigma=5.0),
        default_intensity=30,
        desc="국소 비선형 왜곡",
    ),
    Technique(
        "piecewise", "격자 왜곡", "기타 (왜곡·날씨)",
        lambda t: iaa.PiecewiseAffine(scale=(0.01, max(0.02, _lerp(0.02, 0.05, t)))),
        default_intensity=30,
        desc="격자 기반 국소 변형 (느릴 수 있음)",
    ),
    Technique(
        "fog", "안개", "기타 (왜곡·날씨)",
        lambda t: iaa.Fog(),
        needs_rgb=True,
        default_intensity=50,
        desc="안개 효과 (컬러 전용, 강도 무관)",
    ),
    Technique(
        "clouds", "구름", "기타 (왜곡·날씨)",
        lambda t: iaa.Clouds(),
        needs_rgb=True,
        default_intensity=50,
        desc="구름 효과 (컬러 전용, 강도 무관)",
    ),
]

# key → Technique 빠른 조회
BY_KEY: dict[str, Technique] = {t.key: t for t in TECHNIQUES}


def techniques_by_category() -> dict[str, list[Technique]]:
    """카테고리 → 기법 목록 (CATEGORIES 순서 유지)."""
    out: dict[str, list[Technique]] = {c: [] for c in CATEGORIES}
    for tech in TECHNIQUES:
        out.setdefault(tech.category, []).append(tech)
    return out
