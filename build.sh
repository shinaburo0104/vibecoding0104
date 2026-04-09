#!/usr/bin/env bash
# ================================================================
# F/T Messenger - PyInstaller 빌드 스크립트 (Git Bash / WSL 용)
# build.bat 은 Windows cmd 전용입니다. Bash 에서는 이 파일을 쓰세요.
# 실행 후 dist/FTMessenger.exe 가 생성됩니다.
# ================================================================
set -e

echo "[1/2] PyInstaller 설치 확인..."
python -m pip install --quiet pyinstaller

echo "[2/2] 빌드 시작..."
python -m PyInstaller \
    --noconfirm \
    --onefile \
    --windowed \
    --name "FTMessenger" \
    --collect-all customtkinter \
    --collect-all anthropic \
    --collect-all openai \
    --collect-all google.generativeai \
    --hidden-import pystray._win32 \
    --hidden-import PIL._tkinter_finder \
    main.py

echo
echo "================================================================"
echo "빌드 완료! dist/FTMessenger.exe 를 실행해보세요."
echo "================================================================"
