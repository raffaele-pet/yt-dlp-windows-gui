@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title YT-DLP - Installazione
color 0F

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR_NO_SLASH=%~dp0"
if "%PROJECT_DIR_NO_SLASH:~-1%"=="\" set "PROJECT_DIR_NO_SLASH=%PROJECT_DIR_NO_SLASH:~0,-1%"

set "LINKS_DIR=%LOCALAPPDATA%\Microsoft\WinGet\Links"
set "PYTHON_DIR=%LOCALAPPDATA%\Programs\Python\Python312"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
set "PYTHONW_EXE=%PYTHON_DIR%\pythonw.exe"
set "YTDLP_EXE=%LINKS_DIR%\yt-dlp.exe"
set "FFMPEG_EXE=%LINKS_DIR%\ffmpeg.exe"
set "DENO_EXE=%LINKS_DIR%\deno.exe"

set "PATH=%LINKS_DIR%;%PYTHON_DIR%;%PATH%"
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
if not exist "%PROJECT_DIR%assets\yt-dlp-icon.png" (
    call :fatal "Manca l'icona PNG dell'applicazione."
    exit /b 1
)
if not exist "%PROJECT_DIR%assets\yt-dlp-icon.ico" (
    call :fatal "Manca l'icona Windows dell'applicazione."
    exit /b 1
)

echo [1/6] Controllo dei requisiti...
call :check_all
call :print_status

if "%CHECK_ONLY%"=="1" (
    echo.
    if "!ALL_OK!"=="1" (
        echo [OK] Tutti i requisiti sono disponibili.
        exit /b 0
    ) else (
        echo [MANCANTE] Uno o piu requisiti devono essere installati.
        exit /b 2
    )
)

where winget.exe >nul 2>&1
if errorlevel 1 (
    call :fatal "WinGet non e disponibile. Installa App Installer dal Microsoft Store e riprova."
    exit /b 1
)

echo.
echo [2/6] Installazione dei componenti mancanti...

if "!PYTHON_OK!"=="0" (
    call :install_package "Python.Python.3.12" "Python 3.12" "--scope user"
    if errorlevel 1 exit /b 1
) else (
    echo [SALTA] Python 3.12 e gia disponibile.
)

if "!YTDLP_OK!"=="0" (
    call :install_package "yt-dlp.yt-dlp" "yt-dlp" ""
    if errorlevel 1 exit /b 1
) else (
    echo [SALTA] yt-dlp e gia disponibile.
)

call :check_ffmpeg
if "!FFMPEG_OK!"=="0" (
    call :install_package "yt-dlp.FFmpeg" "FFmpeg per yt-dlp" ""
    if errorlevel 1 exit /b 1
) else (
    echo [SALTA] FFmpeg e gia disponibile.
)

call :check_deno
if "!DENO_OK!"=="0" (
    call :install_package "DenoLand.Deno" "Deno" ""
    if errorlevel 1 exit /b 1
) else (
    echo [SALTA] Deno e gia disponibile.
)

echo.
echo [3/6] Controllo e installazione degli aggiornamenti...
call :python_in_use
if errorlevel 1 (
    echo [RIMANDA] Python 3.12 e in uso da un altro programma: aggiornamento saltato in sicurezza.
    echo           Chiudi i programmi Python e riesegui INSTALL.bat per aggiornarlo.
) else (
    call :upgrade_if_managed "Python.Python.3.12" "Python 3.12"
    if errorlevel 1 exit /b 1
)
call :update_ytdlp
if errorlevel 1 exit /b 1
call :upgrade_if_managed "yt-dlp.FFmpeg" "FFmpeg per yt-dlp"
if errorlevel 1 exit /b 1
call :upgrade_if_managed "DenoLand.Deno" "Deno"
if errorlevel 1 exit /b 1

echo.
echo [4/6] Configurazione dei percorsi...
call :ensure_user_path "%LINKS_DIR%"
if errorlevel 1 (
    call :fatal "Impossibile aggiornare il PATH utente per WinGet."
    exit /b 1
)
call :ensure_user_path "%PYTHON_DIR%"
if errorlevel 1 (
    call :fatal "Impossibile aggiornare il PATH utente per Python."
    exit /b 1
)
echo [OK] PATH utente configurato.

echo.
echo [5/6] Verifica finale e versioni...
call :check_all
call :print_status

if "!ALL_OK!"=="0" (
    call :fatal "La verifica finale non e riuscita. Controlla i messaggi precedenti."
    exit /b 1
)

echo.
echo Versioni rilevate:
echo ---------------------------------------------------------------
set "YTDLP_COMMAND=%YTDLP_EXE%"
set "FFMPEG_COMMAND=%FFMPEG_EXE%"
set "DENO_COMMAND=%DENO_EXE%"
if not exist "!YTDLP_COMMAND!" set "YTDLP_COMMAND=yt-dlp"
if not exist "!FFMPEG_COMMAND!" set "FFMPEG_COMMAND=ffmpeg"
if not exist "!DENO_COMMAND!" set "DENO_COMMAND=deno"
"%PYTHON_EXE%" --version
"!YTDLP_COMMAND!" --version
"!FFMPEG_COMMAND!" -version 2>&1 | findstr /B /C:"ffmpeg version"
"!DENO_COMMAND!" --version 2>&1 | findstr /B /C:"deno "
echo ---------------------------------------------------------------

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


:check_all
call :check_python
call :check_ytdlp
call :check_ffmpeg
call :check_deno
set "ALL_OK=0"
if "!PYTHON_OK!!YTDLP_OK!!FFMPEG_OK!!DENO_OK!"=="1111" set "ALL_OK=1"
exit /b 0


:check_python
set "PYTHON_OK=0"
if exist "%PYTHON_EXE%" if exist "%PYTHONW_EXE%" (
    "%PYTHON_EXE%" --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_OK=1"
)
exit /b 0


:check_ytdlp
set "YTDLP_OK=0"
if exist "%YTDLP_EXE%" (
    "%YTDLP_EXE%" --version >nul 2>&1
    if not errorlevel 1 set "YTDLP_OK=1"
) else (
    yt-dlp --version >nul 2>&1
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
exit /b 0


:print_status
if "!PYTHON_OK!"=="1" (echo   [OK] Python 3.12) else (echo   [MANCANTE] Python 3.12)
if "!YTDLP_OK!"=="1" (echo   [OK] yt-dlp) else (echo   [MANCANTE] yt-dlp)
if "!FFMPEG_OK!"=="1" (echo   [OK] FFmpeg) else (echo   [MANCANTE] FFmpeg)
if "!DENO_OK!"=="1" (echo   [OK] Deno) else (echo   [MANCANTE] Deno)
exit /b 0


:install_package
set "PACKAGE_ID=%~1"
set "PACKAGE_NAME=%~2"
set "PACKAGE_EXTRA=%~3"
echo.
echo ----------------------------------------------------------------
echo [INSTALLA] !PACKAGE_NAME!
echo ----------------------------------------------------------------
winget install --id "!PACKAGE_ID!" --exact --accept-package-agreements --accept-source-agreements --disable-interactivity --silent !PACKAGE_EXTRA!
if errorlevel 1 (
    echo.
    echo [ERRORE] Installazione di !PACKAGE_NAME! non riuscita.
    echo Codice restituito: !errorlevel!
    echo Premi un tasto per chiudere.
    pause >nul
    exit /b 1
)
echo [OK] !PACKAGE_NAME! installato o gia aggiornato.
exit /b 0


:upgrade_if_managed
set "PACKAGE_ID=%~1"
set "PACKAGE_NAME=%~2"
winget list --id "!PACKAGE_ID!" --exact --accept-source-agreements --disable-interactivity >nul 2>&1
if errorlevel 1 (
    echo [NOTA] !PACKAGE_NAME! non e gestito da WinGet: controllo aggiornamenti saltato.
    exit /b 0
)

echo.
echo ----------------------------------------------------------------
echo [AGGIORNA] !PACKAGE_NAME!
echo ----------------------------------------------------------------
winget upgrade --id "!PACKAGE_ID!" --exact --accept-package-agreements --accept-source-agreements --disable-interactivity --silent
set "UPDATE_EXIT=!errorlevel!"
if "!UPDATE_EXIT!"=="0" (
    echo [OK] !PACKAGE_NAME! aggiornato.
    exit /b 0
)
if "!UPDATE_EXIT!"=="-1978335189" (
    echo [OK] !PACKAGE_NAME! e gia aggiornato.
    exit /b 0
)

echo.
echo [ERRORE] Controllo o aggiornamento di !PACKAGE_NAME! non riuscito.
echo Codice restituito: !UPDATE_EXIT!
echo Premi un tasto per chiudere.
pause >nul
exit /b 1


:update_ytdlp
set "YTDLP_COMMAND=%YTDLP_EXE%"
if not exist "!YTDLP_COMMAND!" set "YTDLP_COMMAND=yt-dlp"
set "YTDLP_BEFORE=non disponibile"
for /f "delims=" %%V in ('"!YTDLP_COMMAND!" --version 2^>nul') do set "YTDLP_BEFORE=%%V"
echo.
echo ----------------------------------------------------------------
echo [AGGIORNA] yt-dlp dalla release stabile ufficiale
echo ----------------------------------------------------------------
echo Versione installata: !YTDLP_BEFORE!
echo Controllo il canale stable della repo ufficiale yt-dlp/yt-dlp...
"!YTDLP_COMMAND!" --update-to stable@latest
set "UPDATE_EXIT=!errorlevel!"
if not "!UPDATE_EXIT!"=="0" (
    echo.
    echo [ERRORE] Controllo o aggiornamento di yt-dlp non riuscito.
    echo Codice restituito: !UPDATE_EXIT!
    echo Premi un tasto per chiudere.
    pause >nul
    exit /b 1
)
set "YTDLP_AFTER=non disponibile"
for /f "delims=" %%V in ('"!YTDLP_COMMAND!" --version 2^>nul') do set "YTDLP_AFTER=%%V"
if "!YTDLP_BEFORE!"=="!YTDLP_AFTER!" (
    echo [OK] yt-dlp !YTDLP_AFTER! e gia aggiornato.
) else (
    echo [AGGIORNATO] yt-dlp !YTDLP_BEFORE! --^> !YTDLP_AFTER!
)
exit /b 0


:python_in_use
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
    "$target=[IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312'))+'\'; $processes=@(Get-Process python,pythonw -ErrorAction SilentlyContinue); foreach($process in $processes){if($process.Path -and ([IO.Path]::GetFullPath($process.Path)).StartsWith($target,[StringComparison]::OrdinalIgnoreCase)){exit 1}}; exit 0"
exit /b %errorlevel%


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
