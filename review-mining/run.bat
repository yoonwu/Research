@echo off
cd /d "%~dp0"
echo ============================================
echo  Review collection + analysis (10-20 min)
echo ============================================
if not exist collect_reviews.py (
  echo ERROR: collect_reviews.py not found.
  echo Please run this file inside the review-mining folder.
  pause
  exit /b 1
)
where py >nul 2>nul
if %errorlevel%==0 (set PY=py) else (set PY=python)
%PY% collect_reviews.py
if %errorlevel% neq 0 (
  echo.
  echo Collection failed. Please screenshot this window.
  pause
  exit /b 1
)
%PY% analyze.py
echo.
echo Done! The report opened in your browser.
pause
