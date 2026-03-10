@echo off
chcp 65001 >nul 2>&1
title Billing Software Installer

color 0F
cls
echo.
echo  ================================================================
echo   BILLING SOFTWARE - WINDOWS INSTALLER
echo  ================================================================
echo.
echo  Yeh window band mat karna jab tak COMPLETE na dikhe!
echo.
echo  ================================================================
echo.

:: ----------------------------------------------------------------
:: STEP 1: PYTHON CHECK
:: ----------------------------------------------------------------
echo  [1/8]  Python check kar raha hoon...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        color 4F
        echo.
        echo  ================================================================
        echo   ERROR: Python nahi mila!
        echo  ================================================================
        echo.
        echo   Kya karo:
        echo   1. https://www.python.org/downloads/ kholo
        echo   2. Python 3.11 download karo
        echo   3. Install karo - ADD TO PATH zaroor tick karo
        echo   4. Computer restart karo
        echo   5. Dobara install.bat chalao
        echo.
        pause
        exit /b 1
    )
    set PYTHON=py
) else (
    set PYTHON=python
)

for /f "tokens=*" %%v in ('%PYTHON% --version 2^>^&1') do (
    echo  [1/8]  DONE - %%v mila
)

timeout /t 1 /nobreak >nul

:: ----------------------------------------------------------------
:: STEP 2: DOWNLOAD ZIP
:: ----------------------------------------------------------------
echo.
echo  [2/8]  GitHub se files download kar raha hoon...
echo         (Internet chahiye - 1-2 minute lag sakte hain)
echo.

if exist "billing-main.zip" (
    echo         Purana zip mila - delete kar raha hoon...
    del /f /q "billing-main.zip"
)

powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Write-Host '         Connecting to GitHub...'; Invoke-WebRequest -Uri 'https://github.com/djkalirdp/billing/archive/refs/heads/main.zip' -OutFile 'billing-main.zip' -UseBasicParsing; Write-Host '         Download complete!'"

if not exist "billing-main.zip" (
    color 4F
    echo.
    echo  ================================================================
    echo   ERROR: Download fail ho gaya!
    echo  ================================================================
    echo.
    echo   Reasons:
    echo   - Internet connection check karo
    echo   - GitHub.com khul raha hai browser mein?
    echo   - Antivirus block kar raha ho to temporarily off karo
    echo.
    pause
    exit /b 1
)

for %%A in ("billing-main.zip") do (
    echo  [2/8]  DONE - %%~zA bytes download hua
)

timeout /t 1 /nobreak >nul

:: ----------------------------------------------------------------
:: STEP 3: EXTRACT FILES
:: ----------------------------------------------------------------
echo.
echo  [3/8]  Files extract kar raha hoon...

if exist "billing-main" rmdir /s /q "billing-main"

powershell -NoProfile -Command "Write-Host '         Extracting ZIP...'; Expand-Archive -Path 'billing-main.zip' -DestinationPath '.' -Force; Write-Host '         Done!'"

if not exist "billing-main" (
    color 4F
    echo.
    echo  ERROR: Extract fail ho gaya!
    echo  Dobara chalao
    echo.
    pause
    exit /b 1
)

if not exist "billing-app" mkdir "billing-app"

echo         Files copy kar raha hoon...
xcopy "billing-main\*" "billing-app\" /E /Y /Q >nul 2>&1

if not exist "billing-app\data"            mkdir "billing-app\data"
if not exist "billing-app\backups"         mkdir "billing-app\backups"
if not exist "billing-app\invoices"        mkdir "billing-app\invoices"
if not exist "billing-app\reports"         mkdir "billing-app\reports"
if not exist "billing-app\static\uploads"  mkdir "billing-app\static\uploads"

rmdir /s /q "billing-main"
del /f /q "billing-main.zip"

echo  [3/8]  DONE - billing-app folder ready

timeout /t 1 /nobreak >nul
cd billing-app

:: ----------------------------------------------------------------
:: STEP 4: VIRTUAL ENVIRONMENT
:: ----------------------------------------------------------------
echo.
echo  [4/8]  Python virtual environment bana raha hoon...

if exist "venv\Scripts\python.exe" (
    echo  [4/8]  DONE - Pehle se bana hua hai
) else (
    %PYTHON% -m venv venv
    if %errorlevel% neq 0 (
        color 4F
        echo  ERROR: venv nahi bana! Python reinstall karo
        pause
        exit /b 1
    )
    echo  [4/8]  DONE - Virtual environment ready
)

timeout /t 1 /nobreak >nul

:: ----------------------------------------------------------------
:: STEP 5: PIP UPGRADE
:: ----------------------------------------------------------------
echo.
echo  [5/8]  pip upgrade kar raha hoon...
venv\Scripts\python.exe -m pip install --upgrade pip -q
echo  [5/8]  DONE

timeout /t 1 /nobreak >nul

:: ----------------------------------------------------------------
:: STEP 6: INSTALL PACKAGES
:: ----------------------------------------------------------------
echo.
echo  [6/8]  Python packages install kar raha hoon...
echo         (2-5 minute lag sakte hain - wait karo)
echo.

echo         [1/6] flask...
venv\Scripts\pip.exe install flask -q
echo         [1/6] flask DONE

echo         [2/6] werkzeug...
venv\Scripts\pip.exe install werkzeug -q
echo         [2/6] werkzeug DONE

echo         [3/6] reportlab (PDF engine)...
venv\Scripts\pip.exe install reportlab -q
echo         [3/6] reportlab DONE

echo         [4/6] openpyxl (Excel)...
venv\Scripts\pip.exe install openpyxl -q
echo         [4/6] openpyxl DONE

echo         [5/6] num2words...
venv\Scripts\pip.exe install num2words -q
echo         [5/6] num2words DONE

echo         [6/6] qrcode + Pillow...
venv\Scripts\pip.exe install qrcode[pil] Pillow -q
echo         [6/6] qrcode DONE

echo.
echo  [6/8]  DONE - Saare packages ready

timeout /t 1 /nobreak >nul

:: ----------------------------------------------------------------
:: STEP 7: FONTS
:: ----------------------------------------------------------------
echo.
echo  [7/8]  Rupee symbol fonts download kar raha hoon...

if exist "DejaVuSans.ttf" (
    echo  [7/8]  DONE - Font pehle se hai
) else (
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf' -OutFile 'DejaVuSans.ttf' -UseBasicParsing" >nul 2>&1
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf' -OutFile 'DejaVuSans-Bold.ttf' -UseBasicParsing" >nul 2>&1
    if exist "DejaVuSans.ttf" (
        echo  [7/8]  DONE - Fonts ready
    ) else (
        echo  [7/8]  WARN - Font nahi mila, PDF mein Rs. dikhega
    )
)

timeout /t 1 /nobreak >nul

:: ----------------------------------------------------------------
:: STEP 8: CREATE start.bat
:: ----------------------------------------------------------------
echo.
echo  [8/8]  start.bat bana raha hoon...

(
    echo @echo off
    echo title Billing Software
    echo cd /d "%%~dp0"
    echo cls
    echo color 0A
    echo echo.
    echo echo  ================================================
    echo echo   BILLING SOFTWARE - Running
    echo echo   Browser mein kholo: http://localhost:5000
    echo echo   Login: admin / admin123
    echo echo   Band karne ke liye yeh window band karo
    echo echo  ================================================
    echo echo.
    echo start "" "http://localhost:5000"
    echo venv\Scripts\python.exe app.py
    echo pause
) > start.bat

echo  [8/8]  DONE - start.bat ready

:: ----------------------------------------------------------------
:: VERIFY
:: ----------------------------------------------------------------
echo.
echo  ----------------------------------------------------------------
echo   Quick verify kar raha hoon...
echo  ----------------------------------------------------------------
echo.

venv\Scripts\python.exe -c "import flask; print('  flask    - OK  v' + flask.__version__)" 2>nul || echo   flask    - ERROR
venv\Scripts\python.exe -c "import reportlab; print('  reportlab- OK')" 2>nul || echo   reportlab- ERROR
venv\Scripts\python.exe -c "import openpyxl; print('  openpyxl - OK  v' + openpyxl.__version__)" 2>nul || echo   openpyxl - ERROR
venv\Scripts\python.exe -c "from num2words import num2words; print('  num2words- OK')" 2>nul || echo   num2words- ERROR
venv\Scripts\python.exe -c "import qrcode; print('  qrcode   - OK')" 2>nul || echo   qrcode   - WARN (optional)

:: ----------------------------------------------------------------
:: DONE SCREEN
:: ----------------------------------------------------------------
color 0A
echo.
echo  ================================================================
echo.
echo   INSTALLATION COMPLETE!  Sab kuch ready hai!
echo.
echo  ================================================================
echo.
echo   APP START KARNE KE LIYE:
echo.
echo     billing-app folder mein jaao
echo     start.bat pe DOUBLE-CLICK karo
echo.
echo   Browser mein:  http://localhost:5000
echo   Username:      admin
echo   Password:      admin123
echo.
echo   NOTE: Pehli login ke baad password badlo!
echo.
echo  ================================================================
echo.

set /p STARTNOW=  App abhi start karu? (y/n): 

if /i "%STARTNOW%"=="y" (
    echo.
    echo  Starting app... 3 second mein browser khulega
    echo  Yeh window band MAT karna!
    echo.
    timeout /t 3 /nobreak >nul
    start "" "http://localhost:5000"
    venv\Scripts\python.exe app.py
) else (
    echo.
    echo  Theek hai! Baad mein billing-app\start.bat double-click karna.
    echo.
)

pause
