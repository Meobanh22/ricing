# ==============================================================================
# 🌸 Sylveon Rice One-Click Setup Script for Windows
# ==============================================================================
# Tự động cấu hình toàn bộ setup trên máy mới:
# 1. Cài đặt AutoHotkey v2 và Fastfetch (nếu chưa có)
# 2. Tạo shortcut khởi động cùng Windows cho wallpaper_hotkey.ahk
# 3. Đồng bộ Fastfetch config & ASCII art vào ~/.config/fastfetch
# 4. Kiểm tra/Build wallpaper_switcher.exe nếu cần
# ==============================================================================

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "🌸 Sylveon Rice Setup"

Write-Host "==========================================" -ForegroundColor Magenta
Write-Host "   🌸 SYLVEON RICE ONE-CLICK SETUP 🌸     " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Magenta
Write-Host ""

$Root = $PSScriptRoot

# --- 1. KIỂM TRA & CÀI ĐẶT TOOLS (WINGET) ---
Write-Host "[1/4] Kiểm tra phần mềm cần thiết..." -ForegroundColor Yellow

# Kiểm tra AutoHotkey v2
$ahkPath = (Get-Command AutoHotkey64.exe -ErrorAction SilentlyContinue).Source
if (-not $ahkPath) {
    $possiblePaths = @(
        "$env:LOCALAPPDATA\Programs\AutoHotkey\v2\AutoHotkey64.exe",
        "$env:ProgramFiles\AutoHotkey\v2\AutoHotkey64.exe"
    )
    foreach ($p in $possiblePaths) {
        if (Test-Path $p) { $ahkPath = $p; break }
    }
}

if (-not $ahkPath) {
    Write-Host "  -> Đang cài đặt AutoHotkey v2 qua winget..." -ForegroundColor Cyan
    winget install -e --id AutoHotkey.AutoHotkey --silent --accept-package-agreements --accept-source-agreements
    $ahkPath = "$env:LOCALAPPDATA\Programs\AutoHotkey\v2\AutoHotkey64.exe"
} else {
    Write-Host "  ✔ AutoHotkey v2 đã sẵn sàng: $ahkPath" -ForegroundColor Green
}

# Kiểm tra Fastfetch
if (-not (Get-Command fastfetch -ErrorAction SilentlyContinue)) {
    Write-Host "  -> Đang cài đặt Fastfetch qua winget..." -ForegroundColor Cyan
    winget install -e --id Fastfetch-cli.Fastfetch --silent --accept-package-agreements --accept-source-agreements
} else {
    Write-Host "  ✔ Fastfetch đã sẵn sàng" -ForegroundColor Green
}

# --- 2. THIẾT LẬP STARTUP (TỰ ĐỘNG CHẠY KHI MỞ MÁY) ---
Write-Host "`n[2/4] Cấu hình khởi động cùng Windows (Startup)..." -ForegroundColor Yellow
$startupFolder = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupFolder "WallpaperHotkey.lnk"
$ahkScript = Join-Path $Root "wallpaper_hotkey.ahk"

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
if ($ahkPath -and (Test-Path $ahkPath)) {
    $shortcut.TargetPath = $ahkPath
    $shortcut.Arguments = "`"$ahkScript`""
} else {
    $shortcut.TargetPath = $ahkScript
}
$shortcut.WorkingDirectory = $Root
$shortcut.Save()
Write-Host "  ✔ Đã tạo shortcut khởi động tại: $shortcutPath" -ForegroundColor Green

# --- 3. ĐỒNG BỘ FASTFETCH CONFIG & ASCII ART ---
Write-Host "`n[3/4] Đồng bộ Fastfetch config & ASCII logo..." -ForegroundColor Yellow
$fastfetchDir = Join-Path $HOME ".config\fastfetch"
if (-not (Test-Path $fastfetchDir)) {
    New-Item -ItemType Directory -Path $fastfetchDir -Force | Out-Null
}

# Copy duy nhất logo Sylveon Chibi vào thư mục config của fastfetch
$sylveonArt = "sylveon_chibi.txt"
$src = Join-Path $Root "fastfetch\$sylveonArt"
if (Test-Path $src) {
    Copy-Item $src (Join-Path $fastfetchDir $sylveonArt) -Force
    Write-Host "  ✔ Đã đồng bộ $sylveonArt -> ~/.config/fastfetch/" -ForegroundColor Green
}

# Deploy config.jsonc từ thư mục fastfetch/
$localConfig = Join-Path $Root "fastfetch\config.jsonc"
$targetConfig = Join-Path $fastfetchDir "config.jsonc"
if (Test-Path $localConfig) {
    Copy-Item $localConfig $targetConfig -Force
    Write-Host "  ✔ Đã cập nhật config.jsonc vào ~/.config/fastfetch/" -ForegroundColor Green
}

# --- 4. KIỂM TRA WALLPAPER SWITCHER EXECUTABLE ---
Write-Host "`n[4/4] Kiểm tra Wallpaper Switcher..." -ForegroundColor Yellow
$exePath = Join-Path $Root "wallpaper_switcher.exe"
if (-not (Test-Path $exePath)) {
    if (Get-Command g++ -ErrorAction SilentlyContinue) {
        Write-Host "  -> Đang compile wallpaper_daemon.cpp..." -ForegroundColor Cyan
        & g++ -O2 -mwindows (Join-Path $Root "wallpaper_daemon.cpp") -o $exePath -lole32 -luuid
        Write-Host "  ✔ Compile thành công: wallpaper_switcher.exe" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Chưa tìm thấy g++ và file exe. Hãy copy sẵn wallpaper_switcher.exe vào repo nhé!" -ForegroundColor Red
    }
} else {
    Write-Host "  ✔ File wallpaper_switcher.exe đã sẵn sàng" -ForegroundColor Green
}

# --- 5. CÀI ĐẶT CON TRỎ CHUỘT (SYLVEON CUSTOM) ---
Write-Host "`n[5/5] Cài đặt con trỏ chuột Sylveon Custom..." -ForegroundColor Yellow
$cursorScript = Join-Path $Root "cursors\set_cursor.ps1"
if (Test-Path $cursorScript) {
    & powershell -ExecutionPolicy Bypass -File $cursorScript -Scheme sylveon-custom | Out-Null
    Write-Host "  ✔ Đã kích hoạt con trỏ chuột Sylveon Custom (Chibi + Nơ Ribbon + Wait dải ruy băng xoay)" -ForegroundColor Green
}

# Khởi chạy AHK ngay lập tức
Write-Host "`n🌸 Đang khởi chạy AHK Hotkey..." -ForegroundColor Magenta
Start-Process $ahkScript

Write-Host "`n✨ HOÀN TẤT SETUP! Chúc Mèo Bánh rice máy vui vẻ! ✨`n" -ForegroundColor Cyan

