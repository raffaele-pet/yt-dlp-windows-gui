@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

if not exist "%PYTHON_EXE%" (
    echo Python non trovato: %PYTHON_EXE%
    pause
    exit /b 1
)

"%PYTHON_EXE%" app.py

if errorlevel 1 (
    echo.
    echo L'app si e chiusa con un errore.
    pause
)
