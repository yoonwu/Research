@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo  리뷰 수집 + 분석을 시작합니다 (10~20분 소요)
echo ============================================
where py >nul 2>nul
if %errorlevel%==0 (set PY=py) else (set PY=python)
%PY% collect_reviews.py
if %errorlevel% neq 0 (
  echo.
  echo 수집 중 문제가 발생했습니다. 위 메시지를 캡처해서 알려주세요.
  pause
  exit /b 1
)
%PY% analyze.py
echo.
echo 완료! 브라우저에 보고서가 열렸습니다.
pause
