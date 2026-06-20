@echo off
REM Wrapper for users who prefer double-click or cmd.exe
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-backend.ps1" %*
exit /b %ERRORLEVEL%
