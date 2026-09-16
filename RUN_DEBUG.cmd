@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo Ambiente locale non trovato: %PYTHON_EXE%
    echo Esegui prima INSTALL.bat.
    pause
    exit /b 1
)

"%PYTHON_EXE%" app.py

if errorlevel 1 (
    echo.
    echo L'app si e chiusa con un errore.
    pause
)
