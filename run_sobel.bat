@echo off
REM 외곽선 강조(Sobel) 툴 실행 (imgaug310 conda 환경)
pushd "%~dp0"
"C:\ProgramData\Miniconda3\envs\imgaug310\python.exe" -m sobeltool
popd
