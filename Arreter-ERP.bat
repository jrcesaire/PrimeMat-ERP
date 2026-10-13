@echo off
chcp 65001 >nul
title ERP - Arret des services
cd /d "%~dp0"

echo ============================================
echo   ERP - Arret des serveurs
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERREUR] Python introuvable dans le PATH.
    pause
    exit /b 1
)

python backend\scripts\stop_servers.py

echo.
echo Tous les serveurs sont arretes.
pause
