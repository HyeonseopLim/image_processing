"""폰트 로딩 + 테마(QSS).

한글 최적화:
- assets/fonts/ 에 Pretendard*.ttf 가 있으면 사용, 없으면 Malgun Gothic 폴백
- 자간 -0.3px (QFont AbsoluteSpacing) 적용 → '한국어 최적화' 목표 대응
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

FONTS_DIR = Path(__file__).parent / "assets" / "fonts"

# 색상 팔레트
ACCENT = "#3B82F6"
ACCENT_DARK = "#2563EB"
BG = "#F4F6FB"
CARD = "#FFFFFF"
TEXT = "#1F2937"
MUTED = "#6B7280"
BORDER = "#E5E7EB"


def _load_pretendard() -> str | None:
    """Pretendard ttf 들을 등록하고 패밀리명을 반환. 없으면 None."""
    if not FONTS_DIR.is_dir():
        return None
    family: str | None = None
    for ttf in sorted(FONTS_DIR.glob("Pretendard*.ttf")) + sorted(FONTS_DIR.glob("Pretendard*.otf")):
        fid = QFontDatabase.addApplicationFont(str(ttf))
        if fid >= 0:
            fams = QFontDatabase.applicationFontFamilies(fid)
            if fams:
                family = fams[0]
    return family


def apply_theme(app: QApplication) -> str:
    """앱 폰트·자간·스타일시트 적용. 사용된 폰트 패밀리명을 반환."""
    family = _load_pretendard() or "Malgun Gothic"

    font = QFont(family, 10)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -0.3)  # 자간 -0.3px
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)

    app.setStyleSheet(f"""
        QWidget {{
            background: {BG};
            color: {TEXT};
            font-family: "{family}";
        }}
        QFrame#Card {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: 12px;
        }}
        QLabel#H1 {{ font-size: 18px; font-weight: 700; }}
        QLabel#H2 {{ font-size: 13px; font-weight: 700; color: {TEXT}; }}
        QLabel#Muted {{ color: {MUTED}; font-size: 11px; }}
        QLabel#Category {{
            font-size: 12px; font-weight: 700; color: {ACCENT_DARK};
            padding: 2px 0;
        }}

        QPushButton {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 7px 14px;
            color: {TEXT};
        }}
        QPushButton:hover {{ border-color: {ACCENT}; }}
        QPushButton:pressed {{ background: #EEF2FF; }}
        QPushButton#Primary {{
            background: {ACCENT}; border: none; color: white; font-weight: 700;
        }}
        QPushButton#Primary:hover {{ background: {ACCENT_DARK}; }}
        QPushButton#Primary:disabled {{ background: #A9C3F5; }}
        QPushButton#Danger {{ background: #FEE2E2; border: 1px solid #FCA5A5; color: #B91C1C; }}
        QPushButton#Danger:hover {{ background: #FECACA; }}

        QLineEdit, QSpinBox {{
            background: {CARD}; border: 1px solid {BORDER};
            border-radius: 8px; padding: 6px 8px;
        }}
        QLineEdit:focus, QSpinBox:focus {{ border-color: {ACCENT}; }}

        QCheckBox {{ spacing: 8px; }}
        QCheckBox::indicator {{
            width: 18px; height: 18px; border-radius: 5px;
            border: 1px solid #CBD5E1; background: {CARD};
        }}
        QCheckBox::indicator:checked {{
            background: {ACCENT}; border-color: {ACCENT};
            image: none;
        }}

        QSlider::groove:horizontal {{
            height: 4px; border-radius: 2px; background: {BORDER};
        }}
        QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
        QSlider::handle:horizontal {{
            background: {CARD}; border: 2px solid {ACCENT};
            width: 14px; height: 14px; margin: -6px 0; border-radius: 9px;
        }}
        QSlider:disabled::sub-page:horizontal {{ background: #CBD5E1; }}
        QSlider:disabled::handle:horizontal {{ border-color: #CBD5E1; }}

        QProgressBar {{
            background: {BORDER}; border: none; border-radius: 8px;
            height: 16px; text-align: center; color: {TEXT}; font-size: 11px;
        }}
        QProgressBar::chunk {{ background: {ACCENT}; border-radius: 8px; }}

        QScrollArea {{ border: none; background: transparent; }}
        QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
        QScrollBar::handle:vertical {{ background: #CBD5E1; border-radius: 5px; min-height: 30px; }}
        QScrollBar::handle:vertical:hover {{ background: {MUTED}; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    """)
    return family
