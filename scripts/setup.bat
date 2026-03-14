@echo off
title lifelog - setup
:: プロジェクトルート（scripts の1つ上）を取得
pushd "%~dp0.."
set PROJECT_DIR=%CD%
popd

echo ============================================
echo  lifelog セットアップ
echo ============================================
echo.

:: pipenv の確認
where pipenv >nul 2>&1
if %errorlevel% neq 0 (
  echo [ERROR] pipenv が見つかりません。
  echo   インストール: pip install pipenv
  pause
  exit /b 1
)
echo [OK] pipenv: が見つかりました

:: 依存パッケージのインストール
echo.
echo [lifelog] 依存パッケージをインストールします...
pipenv install
if %errorlevel% neq 0 (
  echo [ERROR] pipenv install に失敗しました
  pause
  exit /b 1
)
echo [OK] インストール完了

:: スタートアップ登録
echo.
echo [lifelog] スタートアップフォルダに登録します...
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set VBS_OUT=%STARTUP%\lifelog-tracker.vbs

:: VBScript を動的生成（パスはこのマシンに合わせて解決済み）
(
  echo Set WshShell = CreateObject^("WScript.Shell"^)
  echo WshShell.CurrentDirectory = "%PROJECT_DIR%"
  echo WshShell.Run "cmd /c cd /d ""%PROJECT_DIR%"" ^&^& pipenv run python tracker.py ^>^> ""%PROJECT_DIR%\data\tracker.log"" 2^>^&1", 0, False
  echo WshShell.Run "cmd /c cd /d ""%PROJECT_DIR%"" ^&^& pipenv run uvicorn api:app --port 8000 ^>^> ""%PROJECT_DIR%\data\api.log"" 2^>^&1", 0, False
) > "%VBS_OUT%"

if %errorlevel% neq 0 (
  echo [ERROR] スタートアップへの登録に失敗しました
  pause
  exit /b 1
)
echo [OK] 登録完了: %VBS_OUT%

:: 今すぐ起動
echo.
echo [lifelog] tracker を起動します...
wscript "%VBS_OUT%"

:: Chrome ショートカット作成
echo.
echo [lifelog] Chrome ショートカットを作成します...
set CHROME_PATH=
for %%p in (
  "%ProgramFiles%\Google\Chrome\Application\chrome.exe"
  "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
  "%LocalAppData%\Google\Chrome\Application\chrome.exe"
) do (
  if exist %%p set CHROME_PATH=%%~p
)

if "%CHROME_PATH%"=="" (
  echo [SKIP] Chrome が見つかりませんでした
) else (
  powershell -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%USERPROFILE%\Desktop\Chrome (lifelog).lnk'); $s.TargetPath='%CHROME_PATH%'; $s.Arguments='--remote-debugging-port=9222'; $s.Description='lifelog URL tracking 用 Chrome'; $s.Save()"
  echo [OK] デスクトップに「Chrome (lifelog).lnk」を作成しました
)

:: Edge ショートカット作成
set EDGE_PATH=
for %%p in (
  "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
  "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
  "%LocalAppData%\Microsoft\Edge\Application\msedge.exe"
) do (
  if exist %%p set EDGE_PATH=%%~p
)

if not "%EDGE_PATH%"=="" (
  powershell -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%USERPROFILE%\Desktop\Edge (lifelog).lnk'); $s.TargetPath='%EDGE_PATH%'; $s.Arguments='--remote-debugging-port=9223'; $s.Description='lifelog URL tracking 用 Edge'; $s.Save()"
  echo [OK] デスクトップに「Edge (lifelog).lnk」を作成しました
)

echo.
echo ============================================
echo  セットアップ完了！
echo  次回ログイン時から自動起動します。
echo.
echo  URL を記録するには:
echo    デスクトップの「Chrome (lifelog)」から起動してください
echo.
echo  ダッシュボードを開くには:
echo    start.bat を実行してください
echo ============================================
echo.
pause
