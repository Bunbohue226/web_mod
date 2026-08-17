@echo off
REM build_exe.bat
REM ---------------------------------------------------------------
REM Dong goi Battle Cats Save Editor thanh 1 thu muc .exe chay duoc,
REM khong can cai Python tren may nguoi dung cuoi.
REM
REM CHAY FILE NAY TREN WINDOWS (khong chay duoc tren Mac/Linux va
REM nguoc lai - PyInstaller khong ho tro build cheo giua cac he
REM dieu hanh, phai build dung tren he dieu hanh muon chay).
REM ---------------------------------------------------------------

echo [1/3] Cai cac thu vien can thiet...
pip install flask==3.1.3 bcsfe==3.6.0 zeroconf pyinstaller
if errorlevel 1 (
    echo LOI: cai thu vien that bai. Kiem tra da cai Python + pip chua.
    exit /b 1
)

echo [2/3] Dang build (co the mat 1-2 phut)...
pyinstaller ^
    --name BattleCatsSaveEditor ^
    --onedir ^
    --console ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --add-data "service-worker.js;." ^
    --collect-data bcsfe ^
    --hidden-import bcsfe ^
    app.py

if errorlevel 1 (
    echo LOI: build that bai, xem log o tren.
    exit /b 1
)

echo [3/3] Xong! File .exe nam trong: dist\BattleCatsSaveEditor\BattleCatsSaveEditor.exe
echo Gui CA THU MUC "dist\BattleCatsSaveEditor" cho nguoi dung (khong chi rieng file .exe).
pause
