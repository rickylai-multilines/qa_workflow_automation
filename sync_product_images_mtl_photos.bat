@echo off
setlocal

REM === Sync product images from MTL PHOTOS share to local Product_images ===
REM Source: UNC path (works from Task Scheduler; no mapped drive required)
REM Behavior:
REM   - Copies files that do NOT exist in the destination.
REM   - Copies files that EXIST but are NEWER on the source (modified date updated).
REM   - Skips files where destination is same age or newer than source.
REM
REM Optional: set RECENT_DAYS to a positive number to only consider source files
REM whose last-write time is within the last N days (reduces network scan).
REM   RECENT_DAYS=0  -> no age filter (recommended for "missing + newer" sync)

set SOURCE=\\mtlerp01\iTrader\mtl\PHOTOS
set DEST=C:\apps\qa_workflow_automation\Product_images
set LOG_FILE=C:\apps\qa_workflow_automation\sync_product_images_mtl_photos.log
set RECENT_DAYS=0

REM Common image extensions only (add more if needed)
set FILESPEC=*.jpg *.jpeg *.png *.gif *.webp *.bmp *.tif *.tiff

if not exist "%DEST%" mkdir "%DEST%"

echo === Sync start %DATE% %TIME% === >> "%LOG_FILE%"
echo SOURCE=%SOURCE% DEST=%DEST% RECENT_DAYS=%RECENT_DAYS% >> "%LOG_FILE%"

REM /E           = subfolders
REM /XO          = exclude older: skip if dest is newer or same; copy if missing or source newer
REM /R:2 /W:5    = retries for network
REM /NP /NDL     = quieter log
REM /NJH /NJS    = suppress job summary headers (optional)
REM /FFT         = assume FAT file times (2-second granularity) if timestamps mismatch
REM /MAXAGE:N    = only files on source modified within last N days (if RECENT_DAYS set)

set "AGE_ARG="
if %RECENT_DAYS% GTR 0 set "AGE_ARG=/MAXAGE:%RECENT_DAYS%"

robocopy "%SOURCE%" "%DEST%" %FILESPEC% /E /XO %AGE_ARG% /R:2 /W:5 /FFT /NP /NDL /NJH /NJS >> "%LOG_FILE%" 2>&1

if %ERRORLEVEL% GEQ 8 (
    echo Sync completed with errors. Exit code: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo Sync completed. Exit code: %ERRORLEVEL% >> "%LOG_FILE%"
)

echo === Sync end %DATE% %TIME% === >> "%LOG_FILE%"
endlocal
