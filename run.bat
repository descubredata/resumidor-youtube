@echo off
REM Arranca el Resumidor de YouTube.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

REM Windows deja que dos servidores compartan el mismo puerto: si eso pasa, unas veces
REM responde el viejo y otras el nuevo, y parece que los cambios no surten efecto.
netstat -ano | findstr /r /c:":8520 .*LISTENING" >nul
if not errorlevel 1 (
    echo.
    echo  El puerto 8520 ya esta ocupado: probablemente la app ya esta abierta.
    echo.
    echo  Abre http://localhost:8520 en el navegador.
    echo  Si quieres arrancarla de cero, cierra la otra ventana negra primero.
    echo.
    pause
    exit /b
)

python -m streamlit run app.py --server.port 8520 --browser.gatherUsageStats false
pause
