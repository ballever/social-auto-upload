@echo off
TITLE One-Click Starter for social-auto-upload

ECHO ==================================================
ECHO  Starting social-auto-upload Servers...
ECHO ==================================================
ECHO.

ECHO [1/2] Starting Python Backend Server (Conda Env) in a new window...

:: 启动新窗口 → 激活 conda → 运行后端
START "SAU Backend" cmd /k "conda activate social-auto-upload && python sau_backend.py"

ECHO.
ECHO ==================================================
ECHO  Done.
ECHO  Two new windows have been opened for the backend
ECHO  and frontend servers. You can monitor logs there.
ECHO ==================================================
ECHO.

ECHO This window will close in 10 seconds...
timeout /t 10 /nobreak > nul
