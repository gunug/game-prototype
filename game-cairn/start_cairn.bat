@echo off
rem Cairn - Blood Olms: server + ngrok, one click.
rem Close: close the two windows ("cairn server", "cairn ngrok").
rem Brain / keys: OPENROUTER_API_KEY (setx). Change model: set CAIRN_OR_MODEL=...
chcp 65001 >nul
cd /d "%~dp0"

if "%NGROK_DOMAIN%"=="" set NGROK_DOMAIN=subregular-zandra-nonwashable.ngrok-free.dev
if "%CAIRN_PORT%"=="" set CAIRN_PORT=8790

rem already running? (port in use)
netstat -ano | findstr /r /c:":%CAIRN_PORT% .*LISTENING" >nul
if %errorlevel%==0 (
  echo [cairn] port %CAIRN_PORT% already in use - server seems to be running. Skipping server start.
) else (
  start "cairn server" cmd /k python "%~dp0server\cairn_server.py" --port %CAIRN_PORT%
  ping -n 3 127.0.0.1 >nul
)

tasklist | findstr /i ngrok.exe >nul
if %errorlevel%==0 (
  echo [cairn] ngrok already running - leaving it as is.
) else (
  start "cairn ngrok" cmd /k ngrok http %CAIRN_PORT% --url "https://%NGROK_DOMAIN%"
  ping -n 4 127.0.0.1 >nul
)

echo.
echo   local : http://localhost:%CAIRN_PORT%
echo   public: https://%NGROK_DOMAIN%
echo   password: server\cairn.pass
echo.
start "" "http://localhost:%CAIRN_PORT%"
ping -n 6 127.0.0.1 >nul
