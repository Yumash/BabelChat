@echo off
echo === WoWTranslator Clean Build ===

echo Cleaning build cache...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Building...
python -m PyInstaller --clean --noconfirm build.spec

if %errorlevel% neq 0 (
    echo BUILD FAILED
    exit /b %errorlevel%
)

echo.
echo Build OK: dist\WoWTranslator.exe
