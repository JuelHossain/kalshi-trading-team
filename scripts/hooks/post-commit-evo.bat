@echo off
REM Post-commit hook for automatic documentation evolution (Windows)
REM This hook runs after each commit to handle async documentation updates

setlocal EnableDelayedExpansion

REM Get the project root (parent of scripts\hooks\)
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
cd /d "%PROJECT_ROOT%"

REM Check if evolution system is enabled
if not "%EVOLUTION_DISABLED%"=="" (
    echo [Evolution] System disabled via EVOLUTION_DISABLED environment variable
    exit /b 0
)

REM Get commit information
for /f "tokens=*" %%a in ('git rev-parse HEAD') do set "COMMIT_HASH=%%a"
for /f "tokens=*" %%a in ('git log -1 --pretty^=%%B') do set "COMMIT_MSG=%%a"
for /f "tokens=*" %%a in ('git rev-parse --abbrev-ref HEAD') do set "BRANCH=%%a"

echo [Evolution] Queuing async documentation updates for commit %COMMIT_HASH:~0,8%...

REM Run async updates in the background using start
REM This allows the commit to complete without waiting for documentation updates
start /B python scripts\evolution\orchestrator.py async --commit "%COMMIT_HASH%" --message "%COMMIT_MSG%" > %TEMP%\evolution_async.log 2>&1

echo [Evolution] Async updates running in background

exit /b 0
