@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title YT-DLP - Installazione e aggiornamento
color 0F

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR_NO_SLASH=%~dp0"
if "%PROJECT_DIR_NO_SLASH:~-1%"=="\" set "PROJECT_DIR_NO_SLASH=%PROJECT_DIR_NO_SLASH:~0,-1%"
set "VENV_DIR=%PROJECT_DIR%.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "VENV_PYW=%VENV_DIR%\Scripts\pythonw.exe"
set "VENV_YTDLP=%VENV_DIR%\Scripts\yt-dlp.exe"
set "LINKS_DIR=%LOCALAPPDATA%\Microsoft\WinGet\Links"
set "FFMPEG_EXE=%LINKS_DIR%\ffmpeg.exe"
set "DENO_EXE=%LINKS_DIR%\deno.exe"
set "PATH=%LINKS_DIR%;%PATH%"
set "CHECK_ONLY=0"
if /I "%~1"=="--check" set "CHECK_ONLY=1"

echo ================================================================
echo                       YT-DLP INSTALLER
echo ================================================================
echo Cartella progetto: %PROJECT_DIR_NO_SLASH%
echo.

if not exist "%PROJECT_DIR%app.py" (
    call :fatal "Manca il file app.py nella cartella del progetto."
    exit /b 1
)
if not exist "%PROJECT_DIR%RUN.vbs" (
    call :fatal "Manca il file RUN.vbs nella cartella del progetto."
    exit /b 1
)
if not exist "%PROJECT_DIR%requirements.txt" (
    call :fatal "Manca il file requirements.txt nella cartella del progetto."
    exit /b 1
)
if not exist "%PROJECT_DIR%assets\yt-dlp-icon.png" (
    call :fatal "Manca l'icona PNG dell'applicazione."
    exit /b 1
)
if not exist "%PROJECT_DIR%assets\yt-dlp-icon.ico" (
    call :fatal "Manca l'icona Windows dell'applicazione."
    exit /b 1
)

call :find_python
call :check_venv
call :check_ffmpeg
call :check_deno

if "%CHECK_ONLY%"=="1" (
    call :print_status
    if "!PYTHON_OK!!VENV_OK!!YTDLP_OK!!FFMPEG_OK!!DENO_OK!"=="11111" exit /b 0
    exit /b 2
)

where winget.exe >nul 2>&1
if errorlevel 1 (
    call :fatal "WinGet non e disponibile. Installa App Installer dal Microsoft Store e riprova."
    exit /b 1
)

echo [1/6] Controllo di Python...
if "!PYTHON_OK!"=="0" (
    echo [INSTALLA] Python 3.13: non e stata trovata alcuna versione compatibile.
    winget install --id "Python.Python.3.13" --exact --scope user --accept-package-agreements --accept-source-agreements --disable-interactivity
    if errorlevel 1 (
        call :fatal "Installazione di Python 3.13 non riuscita."
        exit /b 1
    )
    call :find_python
)
if "!PYTHON_OK!"=="0" (
    call :fatal "Python 3.11 o successivo non e stato trovato dopo l'installazione."
    exit /b 1
)
echo [OK] Uso !PYTHON_VERSION!: !PYTHON_EXE!
echo      Python di sistema non verra duplicato ne aggiornato dall'installer.

echo.
echo [2/6] Preparazione dell'ambiente isolato .venv...
if exist "%VENV_DIR%" if "!VENV_OK!"=="0" (
    echo [RIPARA] L'ambiente locale esistente non e piu valido e verra ricreato.
    rmdir /s /q "%VENV_DIR%"
)
if not exist "%VENV_PY%" (
    "!PYTHON_EXE!" -m venv "%VENV_DIR%"
    if errorlevel 1 (
        call :fatal "Creazione dell'ambiente .venv non riuscita."
        exit /b 1
    )
) else (
    echo [OK] Ambiente .venv gia presente.
)
"%VENV_PY%" -m pip install --disable-pip-version-check --upgrade pip setuptools wheel
if errorlevel 1 (
    call :fatal "Aggiornamento degli strumenti dell'ambiente .venv non riuscito."
    exit /b 1
)

echo.
echo [3/6] Controllo e aggiornamento di yt-dlp nell'ambiente .venv...
set "YTDLP_BEFORE=non installato"
if exist "%VENV_YTDLP%" for /f "delims=" %%V in ('"%VENV_YTDLP%" --version 2^>nul') do set "YTDLP_BEFORE=%%V"
echo Versione presente: !YTDLP_BEFORE!
echo Controllo l'ultima release stabile ufficiale...
"%VENV_PY%" -m pip install --disable-pip-version-check --upgrade -r "%PROJECT_DIR%requirements.txt"
if errorlevel 1 (
    call :fatal "Installazione o aggiornamento di yt-dlp nella .venv non riuscito."
    exit /b 1
)
set "YTDLP_AFTER=non disponibile"
for /f "delims=" %%V in ('"%VENV_YTDLP%" --version 2^>nul') do set "YTDLP_AFTER=%%V"
if "!YTDLP_BEFORE!"=="!YTDLP_AFTER!" (
    echo [OK] yt-dlp !YTDLP_AFTER! e gia aggiornato.
) else (
    echo [AGGIORNATO] yt-dlp !YTDLP_BEFORE! --^> !YTDLP_AFTER!
)

echo.
echo [4/6] Controllo di FFmpeg e Deno...
call :check_ffmpeg
if "!FFMPEG_OK!"=="0" (
    call :install_package "yt-dlp.FFmpeg" "FFmpeg per yt-dlp"
    if errorlevel 1 exit /b 1
) else (
    echo [OK] FFmpeg gia disponibile.
    call :upgrade_if_managed "yt-dlp.FFmpeg" "FFmpeg per yt-dlp"
    if errorlevel 1 exit /b 1
)
call :check_deno
if "!DENO_OK!"=="0" (
    call :install_package "DenoLand.Deno" "Deno"
    if errorlevel 1 exit /b 1
) else (
    echo [OK] Deno gia disponibile.
    call :upgrade_if_managed "DenoLand.Deno" "Deno"
    if errorlevel 1 exit /b 1
)
call :ensure_user_path "%LINKS_DIR%"
if errorlevel 1 (
    call :fatal "Impossibile aggiornare il PATH utente per WinGet."
    exit /b 1
)
call :check_ffmpeg
call :check_deno
if exist "!FFMPEG_EXE!" for %%D in ("!FFMPEG_EXE!") do (
    call :ensure_user_path "%%~dpD"
    set "PATH=%%~dpD;!PATH!"
)
if exist "!DENO_EXE!" for %%D in ("!DENO_EXE!") do (
    call :ensure_user_path "%%~dpD"
    set "PATH=%%~dpD;!PATH!"
)

echo.
echo [5/6] Verifica finale...
call :find_python
call :check_venv
call :check_ffmpeg
call :check_deno
call :print_status
if not "!PYTHON_OK!!VENV_OK!!YTDLP_OK!!FFMPEG_OK!!DENO_OK!"=="11111" (
    call :fatal "La verifica finale non e riuscita. Controlla i messaggi precedenti."
    exit /b 1
)
"%VENV_PY%" -m py_compile "%PROJECT_DIR%app.py"
if errorlevel 1 (
    call :fatal "app.py contiene un errore di sintassi."
    exit /b 1
)

echo.
echo [6/6] Creazione del collegamento sul Desktop...
set "YT_DLP_PROJECT=%PROJECT_DIR_NO_SLASH%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
    "$project=$env:YT_DLP_PROJECT; $desktop=[Environment]::GetFolderPath('Desktop'); $shortcut=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $desktop 'YT-DLP.lnk')); $shortcut.TargetPath=(Join-Path $env:WINDIR 'System32\wscript.exe'); $shortcut.Arguments=([char]34)+(Join-Path $project 'RUN.vbs')+([char]34); $shortcut.WorkingDirectory=$project; $shortcut.Description='Avvia l''interfaccia YT-DLP'; $shortcut.IconLocation=(Join-Path $project 'assets\yt-dlp-icon.ico')+',0'; $shortcut.Save()"
if errorlevel 1 (
    call :fatal "Impossibile creare il collegamento sul Desktop."
    exit /b 1
)
echo [OK] Collegamento YT-DLP creato sul Desktop.

echo.
echo ================================================================
echo INSTALLAZIONE COMPLETATA CON SUCCESSO
echo ================================================================
echo.

choice /C SN /N /M "Vuoi avviare YT-DLP ora? [S/N]: "
if errorlevel 2 goto :finish
start "" "%WINDIR%\System32\wscript.exe" "%PROJECT_DIR%RUN.vbs"

:finish
echo.
echo Premi un tasto per chiudere questa finestra.
pause >nul
exit /b 0


:find_python
set "PYTHON_OK=0"
set "PYTHON_EXE="
set "PYTHON_VERSION=non disponibile"
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" call :try_python "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do if not defined PYTHON_EXE call :try_python "%%P"
for /f "delims=" %%P in ('where python.exe 2^>nul') do if not defined PYTHON_EXE call :try_python "%%P"
exit /b 0


:try_python
if defined PYTHON_EXE exit /b 0
if not exist "%~1" exit /b 0
"%~1" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 exit /b 0
set "PYTHON_EXE=%~1"
set "PYTHON_OK=1"
for /f "delims=" %%V in ('"%~1" --version 2^>^&1') do set "PYTHON_VERSION=%%V"
exit /b 0


:check_venv
set "VENV_OK=0"
set "YTDLP_OK=0"
set "YTDLP_VERSION=non disponibile"
if exist "%VENV_PY%" if exist "%VENV_PYW%" (
    "%VENV_PY%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
    if not errorlevel 1 set "VENV_OK=1"
)
if "!VENV_OK!"=="1" if exist "%VENV_YTDLP%" (
    for /f "delims=" %%V in ('"%VENV_YTDLP%" --version 2^>nul') do set "YTDLP_VERSION=%%V"
    "%VENV_YTDLP%" --version >nul 2>&1
    if not errorlevel 1 set "YTDLP_OK=1"
)
exit /b 0


:check_ffmpeg
set "FFMPEG_OK=0"
if exist "%FFMPEG_EXE%" (
    "%FFMPEG_EXE%" -version >nul 2>&1
    if not errorlevel 1 set "FFMPEG_OK=1"
) else (
    ffmpeg -version >nul 2>&1
    if not errorlevel 1 set "FFMPEG_OK=1"
)
if "!FFMPEG_OK!"=="0" for /f "delims=" %%P in ('where /r "%LOCALAPPDATA%\Microsoft\WinGet\Packages" ffmpeg.exe 2^>nul') do if "!FFMPEG_OK!"=="0" (
    "%%P" -version >nul 2>&1
    if not errorlevel 1 (
        set "FFMPEG_EXE=%%P"
        set "FFMPEG_OK=1"
    )
)
exit /b 0


:check_deno
set "DENO_OK=0"
if exist "%DENO_EXE%" (
    "%DENO_EXE%" --version >nul 2>&1
    if not errorlevel 1 set "DENO_OK=1"
) else (
    deno --version >nul 2>&1
    if not errorlevel 1 set "DENO_OK=1"
)
if "!DENO_OK!"=="0" for /f "delims=" %%P in ('where /r "%LOCALAPPDATA%\Microsoft\WinGet\Packages" deno.exe 2^>nul') do if "!DENO_OK!"=="0" (
    "%%P" --version >nul 2>&1
    if not errorlevel 1 (
        set "DENO_EXE=%%P"
        set "DENO_OK=1"
    )
)
exit /b 0


:print_status
if "!PYTHON_OK!"=="1" (echo   [OK] !PYTHON_VERSION! di sistema) else (echo   [MANCANTE] Python 3.11 o successivo)
if "!VENV_OK!"=="1" (echo   [OK] Ambiente locale .venv) else (echo   [MANCANTE] Ambiente locale .venv)
if "!YTDLP_OK!"=="1" (echo   [OK] yt-dlp !YTDLP_VERSION! nella .venv) else (echo   [MANCANTE] yt-dlp nella .venv)
if "!FFMPEG_OK!"=="1" (echo   [OK] FFmpeg) else (echo   [MANCANTE] FFmpeg)
if "!DENO_OK!"=="1" (echo   [OK] Deno) else (echo   [MANCANTE] Deno)
exit /b 0


:install_package
set "PACKAGE_ID=%~1"
set "PACKAGE_NAME=%~2"
echo.
echo ----------------------------------------------------------------
echo [INSTALLA] !PACKAGE_NAME!
echo ----------------------------------------------------------------
winget install --id "!PACKAGE_ID!" --exact --accept-package-agreements --accept-source-agreements --disable-interactivity --silent
if errorlevel 1 (
    call :fatal "Installazione di !PACKAGE_NAME! non riuscita."
    exit /b 1
)
echo [OK] !PACKAGE_NAME! installato.
exit /b 0


:upgrade_if_managed
set "PACKAGE_ID=%~1"
set "PACKAGE_NAME=%~2"
winget list --id "!PACKAGE_ID!" --exact --accept-source-agreements --disable-interactivity >nul 2>&1
if errorlevel 1 exit /b 0
winget upgrade --id "!PACKAGE_ID!" --exact --accept-package-agreements --accept-source-agreements --disable-interactivity --silent >nul 2>&1
set "UPDATE_EXIT=!errorlevel!"
if "!UPDATE_EXIT!"=="0" exit /b 0
if "!UPDATE_EXIT!"=="-1978335189" exit /b 0
call :fatal "Controllo o aggiornamento di !PACKAGE_NAME! non riuscito. Codice !UPDATE_EXIT!."
exit /b 1


:ensure_user_path
set "PATH_TO_ADD=%~1"
set "YT_DLP_PATH_TO_ADD=%PATH_TO_ADD%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
    "$dir=$env:YT_DLP_PATH_TO_ADD.TrimEnd('\'); $current=[Environment]::GetEnvironmentVariable('Path','User'); $entries=if($current){$current -split ';'}else{@()}; if(-not ($entries | Where-Object { $_.Trim().TrimEnd('\') -ieq $dir })){[Environment]::SetEnvironmentVariable('Path',(($dir+';'+$current).TrimEnd(';')),'User')}"
exit /b %errorlevel%


:fatal
echo.
echo ================================================================
echo [ERRORE] %~1
echo ================================================================
if "%CHECK_ONLY%"=="1" exit /b 1
echo Premi un tasto per chiudere questa finestra.
pause >nul
exit /b 1
