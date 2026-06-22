# image_processing

[imgaug](https://github.com/aleju/imgaug) 기반 이미지 증폭(augmentation) 툴.

TIFF / JPEG / BMP 이미지를 입력받아, 원하는 변환 기법과 강도를 선택해
지정한 개수만큼 증폭 이미지를 생성한다.

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

🚧 개발 초기 — 구조 설계 중

(추후 작성: 입력 폴더 지정 → 변환 기법/강도 선택 → 증폭 개수 지정 → 실행)

---

## 4. git

- 원격: `git@github.com:HyeonseopLim/image_processing.git`
- 기본 브랜치: `main`
