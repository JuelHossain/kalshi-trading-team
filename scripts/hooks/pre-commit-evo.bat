@echo off
REM Pre-commit hook for automatic documentation evolution (Windows)
REM This hook runs before each commit to analyze changes and update docs synchronously

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

echo [Evolution] Analyzing staged changes...

REM Run the analyzer to check significance
python scripts\evolution\analyzer.py pre-commit --json > %TEMP%\evo_analysis.json 2>nul
if errorlevel 1 (
    echo [Evolution] Analyzer failed, skipping updates
    exit /b 0
)

REM Parse the JSON output to check if significant
python -c "import sys, json; d=json.load(open(r'%TEMP%\evo_analysis.json')); sys.exit(0 if d.get('is_significant') else 1)"
if errorlevel 1 (
    echo [Evolution] No significant changes detected - skipping sync updates
    exit /b 0
)

echo [Evolution] Significant changes detected - running synchronous updates...

REM Run sync updates
python scripts\evolution\orchestrator.py sync
if errorlevel 1 (
    echo [Evolution] Warning: Sync updates had errors, but allowing commit to proceed
)

REM Stage any documentation files that were updated
git add ai-env\

echo [Evolution] Documentation updated and staged

REM Always succeed - we don't want to block commits
exit /b 0
