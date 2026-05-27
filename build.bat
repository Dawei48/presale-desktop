@echo off
chcp 65001 >nul
echo.
echo ══════════════════════════════════════════
echo   放心预 - 构建 .exe 安装包
echo ══════════════════════════════════════════
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

:: 安装依赖
echo [1/3] 安装依赖...
pip install -r requirements.txt >nul 2>&1
pip install pyinstaller >nul 2>&1

:: 构建
echo [2/3] 构建 .exe ...
pyinstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "放心预" ^
    --add-data "config.py;." ^
    --add-data "database.py;." ^
    --add-data "ui;ui" ^
    --add-data "utils;utils" ^
    --hidden-import customtkinter ^
    --hidden-import docx ^
    main.py

:: 复制数据目录
echo [3/3] 整理输出...
if not exist "dist\data" mkdir "dist\data"

echo.
echo ══════════════════════════════════════════
echo   构建完成！
echo   输出位置: dist\放心预.exe
echo ══════════════════════════════════════════
echo.
pause
