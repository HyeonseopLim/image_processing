# image_processing

이미지 처리 도구 모음.

| 도구 | 실행 | 설명 |
|------|------|------|
| **이미지 증폭** | `run.bat` / `python -m augtool` | [imgaug](https://github.com/aleju/imgaug) 기반. 변환 기법·강도 선택해 지정 개수만큼 증폭 |
| **외곽선 강조 (Sobel)** | `run_sobel.bat` / `python -m sobeltool` | 폴더 내 이미지의 외곽선을 Sobel/Scharr/Laplacian/Canny 로 강조 |

> 증폭 툴: TIFF / JPEG / BMP 이미지를 입력받아, 원하는 변환 기법과 강도를 선택해
> 지정한 개수만큼 증폭 이미지를 생성한다.

---

## 1. 개발 환경

| 항목 | 값 |
|------|----|
| OS | Windows 11 |
| Python | 3.10.20 |
| 가상환경 도구 | Miniconda (`C:\ProgramData\Miniconda3`) |
| conda 환경명 | **`imgaug310`** |
| 환경 경로 | `C:\ProgramData\Miniconda3\envs\imgaug310` |

### 핵심 의존성 (`requirements.txt`)

| 패키지 | 버전 | 비고 |
|--------|------|------|
| imgaug | 0.4.0 | 증폭 엔진 |
| numpy | **1.23.5** | ⚠️ 2.x 금지 (아래 참고) |
| scipy | 1.10.1 | numpy 1.x 호환 |
| scikit-image | 0.19.3 | numpy 1.x 호환 |
| matplotlib | 3.7.5 | numpy 1.x 호환 |
| opencv-python | 4.10.0.84 | 4.11+ 는 numpy≥2 요구 |
| Pillow | 12.2.0 | 이미지 입출력 |
| imageio | 2.37.3 | TIFF 등 입출력 |
| PySide6 | 6.11.1 | GUI |

> ### ⚠️ numpy 버전 주의 (중요)
> imgaug 0.4.0(2020년 마지막 릴리스)은 **numpy 2.0에서 제거된 `np.sctypes`** 를
> 사용하므로 numpy 2.x 환경에서는 `import imgaug` 자체가 실패한다.
> 또한 numpy 1.24에서 제거된 `np.bool`/`np.float` 별칭도 일부 사용한다.
> 따라서 **numpy 1.23.5** 로 고정해야 하며, 이에 맞춰
> scipy·scikit-image·matplotlib·opencv 도 numpy 1.x 호환 버전으로 핀 고정되어 있다.
> `requirements.txt` 의 버전을 임의로 올리지 말 것.

---

## 2. 환경 구축 방법

처음 세팅하거나 다른 PC에서 복원할 때:

```bash
# 1) conda 환경 생성
conda create -n imgaug310 python=3.10 -y
conda activate imgaug310

# 2) 의존성 설치 (버전 고정)
pip install -r requirements.txt
```

> Git Bash 에서 `conda.exe` 를 직접 호출하면 `CondaSSLError`(OpenSSL 미발견)가
> 날 수 있다. 이 경우 PATH 에 `C:\ProgramData\Miniconda3\Library\bin` 을 추가하거나
> Anaconda Prompt / `conda activate` 를 거친 셸에서 실행한다.

### 설치 검증

```bash
python -c "import imgaug.augmenters as iaa, numpy as np; \
img=(np.random.rand(128,128,3)*255).astype('uint8'); \
print('OK', iaa.Affine(rotate=45)(image=img).shape)"
```

`OK (128, 128, 3)` 가 출력되면 정상.

---

## 3. 사용법

### 실행

```bash
# 방법 1: 배치 파일 (더블클릭)
run.bat

# 방법 2: 직접 실행
conda activate imgaug310
python -m augtool
```

### 작업 흐름

1. **입력 폴더** 선택 → 폴더 안의 TIFF/JPEG/BMP 자동 탐색 (개수 표시)
2. **변환 기법** 선택 (체크박스) + **강도** 조절 (슬라이더 0~100%)
   - 좌측 패널에서 카테고리별로 선택, 선택/강도 변경 시 우측 **미리보기** 실시간 갱신
3. **증폭 개수** 지정 (이미지당 N개) → 총 생성 예정 개수 표시
4. **출력 폴더** 선택 (미지정 시 입력폴더 아래 `augmented/`)
5. **증폭 시작** → 진행바로 진행 상황 확인, 중간 **중지** 가능

- 출력 파일명: `{원본이름}_aug001.{확장자}` … (확장자·그레이스케일 여부 보존)

### 변환 기법 (4개 카테고리, 총 23종)

| 카테고리 | 기법 |
|----------|------|
| 기하학 변환 | 회전, 좌우/상하 반전, 이동, 확대·축소, 전단, 원근 변형 |
| 밝기·색상 | 밝기, 대비, 감마, 채도, 색조, 그레이스케일 |
| 노이즈·블러 | 가우시안 노이즈/블러, 모션 블러, 드롭아웃, 소금·후추 |
| 기타 (왜곡·날씨) | 선명화, 탄성 변형, 격자 왜곡, 안개, 구름 |

> 채도·색조·안개·구름 등 일부는 컬러(RGB) 전용이며, 그레이스케일 입력에는 효과가 제한적이다.

---

## 3-B. 외곽선 강조 (Sobel) 툴

```bash
run_sobel.bat        # 또는  python -m sobeltool
```

1. **입력 폴더** 선택 → TIFF/JPEG/BMP/PNG 자동 탐색
2. **엣지 방식** 선택: Sobel / Scharr(정밀) / Laplacian / Canny
3. **출력 모드**: `외곽선 강조`(원본에 엣지 덧입힘) / `외곽선만`(엣지 맵)
4. 파라미터: 커널 크기(1·3·5·7), 강도(0~3), Canny 임계값, 반전
   - 변경 시 우측 **미리보기** 실시간 갱신
5. **외곽선 변환 시작** → `{원본이름}_edge.{확장자}` 로 저장 (포맷·채널 보존)

---

## 4. 프로젝트 구조

```
image_processing/
├── run.bat                  # 증폭 툴 실행
├── run_sobel.bat            # 외곽선 강조 툴 실행
├── requirements.txt
├── augtool/                 # 이미지 증폭 툴
│   ├── __main__.py          # python -m augtool 진입점
│   ├── core/
│   │   ├── augmenters.py     # 변환 기법 레지스트리(강도→imgaug)
│   │   └── pipeline.py       # 이미지 입출력 + 배치 증폭
│   └── ui/
│       ├── style.py          # 폰트(Pretendard/Malgun)·자간·테마 (공용)
│       ├── widgets.py        # 기법 선택 위젯
│       ├── worker.py         # QThread 백그라운드 증폭
│       ├── main_window.py    # 메인 윈도우
│       └── assets/fonts/     # Pretendard 폰트 위치(선택)
└── sobeltool/               # 외곽선 강조 툴
    ├── __main__.py          # python -m sobeltool 진입점
    ├── core.py              # 엣지 검출 + 외곽선 강조 + 배치
    └── ui.py                # GUI (augtool 테마 재사용)
```

---

## 5. git

- 원격: `git@github.com:HyeonseopLim/image_processing.git`
- 기본 브랜치: `main`
