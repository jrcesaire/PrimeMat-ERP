@echo off
chcp 65001 >nul
title ERP - Demarrage des services
cd /d "%~dp0"

echo ============================================
echo   ERP Materiaux de Construction - Demarrage
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERREUR] Python introuvable dans le PATH.
    pause
    exit /b 1
)

echo [1/3] Arret des anciens serveurs...
python backend\scripts\stop_servers.py
echo.

echo [2/3] Demarrage des backends (ports 8001 et 8002)...
python backend\scripts\restart_servers.py
echo.

echo [3/3] Demarrage du frontend (port 3000)...
python backend\scripts\start_frontend.py
echo.

echo ============================================
echo   Verification
echo ============================================
python backend\scripts\health_check.py
echo.

echo Si les 3 lignes ci-dessus affichent "HTTP 200",
echo ouvrez votre navigateur sur :  http://localhost:3000
echo Login : admin@abc.com  /  Code entreprise : GEA
echo.
echo Vous pouvez fermer cette fenetre, les serveurs
echo continuent de tourner en arriere-plan.
pause
