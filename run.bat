@echo off
REM 이미지 증폭 도구 실행 (imgaug310 conda 환경)
pushd "%~dp0"
"C:\ProgramData\Miniconda3\envs\imgaug310\python.exe" -m augtool
popd
