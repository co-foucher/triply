@echo off
setlocal
title coroforge - keep this window open while you use the app
cd /d "%~dp0"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

rem --- 1) Install uv for this user only, no admin rights, if it is missing
where uv >nul 2>nul
if errorlevel 1 (
    echo Installing uv ...
    powershell -NoProfile -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    where uv >nul 2>nul
    if errorlevel 1 goto :fail_uv
)

rem --- 2) Pre-answer Streamlit's one-time "Email:" question. Otherwise the
rem        first launch waits silently for keyboard input and no browser opens.
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
    > "%USERPROFILE%\.streamlit\credentials.toml" echo [general]
    >> "%USERPROFILE%\.streamlit\credentials.toml" echo email = ""
)

rem --- 3) Install or update the packages, then start the GUI in the browser
echo.
echo Starting coroforge. The first launch downloads about 450 MB
echo and can take several minutes. Later launches start in seconds.
echo.
uv run --extra gui streamlit run app\Home.py
if errorlevel 1 goto :fail_run
exit /b 0

:fail_uv
echo.
echo ERROR: uv could not be installed. Check the internet connection or proxy.
pause
exit /b 1

:fail_run
echo.
echo The app has stopped. If that was unexpected, read the messages above.
pause
exit /b 1
