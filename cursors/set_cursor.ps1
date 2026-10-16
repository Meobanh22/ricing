# ==============================================================================
# 🖱️ Apply Cursor Scheme (Zero Admin Required)
# ==============================================================================
param(
    [ValidateSet("sylveon-custom", "sylveon-paw", "sylveon-chibi", "sylveon-animated", "pokemon", "catppuccin", "default")]
    [string]$Scheme = "sylveon-custom"
)

$regPath = "HKCU:\Control Panel\Cursors"
$schemesKey = "HKCU:\Control Panel\Cursors\Schemes"
if (-not (Test-Path $schemesKey)) { New-Item -Path $schemesKey -Force | Out-Null }

$code = @"
using System;
using System.Runtime.InteropServices;
public class LiveCursorSetter2 {
    [DllImport("user32.dll", EntryPoint = "LoadCursorFromFileW", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern IntPtr LoadCursorFromFile(string path);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool SetSystemCursor(IntPtr hcur, uint id);

    [DllImport("user32.dll", EntryPoint = "SystemParametersInfoW", SetLastError = true)]
    public static extern bool SystemParametersInfo(uint uiAction, uint uiParam, IntPtr pvParam, uint fWinIni);
}
"@
if (-not ([System.Management.Automation.PSTypeName]'LiveCursorSetter2').Type) {
    Add-Type -TypeDefinition $code
}

if ($Scheme -eq "sylveon-custom") {
    Write-Host "🎀 Đang áp dụng trọn bộ con trỏ Sylveon Custom (Trọn bộ 14 con trỏ từ Sheet + Wait vẽ tay xoay 360°)..." -ForegroundColor Magenta
    $DestDir = "$env:LOCALAPPDATA\Cursors\Sylveon Custom"
    if (-not (Test-Path $DestDir)) { New-Item -ItemType Directory -Path $DestDir -Force | Out-Null }
    
    $sourceDir = "$PSScriptRoot\sylveon_custom"
    
    # Copy toàn bộ 14 files cursor custom
    $files = @(
        "sylveon_arrow.cur", "sylveon_help.cur", "sylveon_text.cur", "sylveon_busy.cur",
        "sylveon_precision.cur", "sylveon_link.cur", "sylveon_unavailable.cur",
        "sylveon_vertical_resize.cur", "sylveon_horizontal_resize.cur",
        "sylveon_diagonal_resize1.cur", "sylveon_diagonal_resize2.cur",
        "sylveon_move.cur", "sylveon_alternate.cur", "sylveon_wait.ani"
    )
    foreach ($f in $files) {
        Copy-Item "$sourceDir\$f" "$DestDir\$f" -Force
    }

    $arrowCur        = "$DestDir\sylveon_arrow.cur"
    $helpCur         = "$DestDir\sylveon_help.cur"
    $appStartingCur  = "$DestDir\sylveon_busy.cur"
    $waitAni         = "$DestDir\sylveon_wait.ani"
    $crosshairCur    = "$DestDir\sylveon_precision.cur"
    $textCur         = "$DestDir\sylveon_text.cur"
    $penCur          = "$DestDir\sylveon_alternate.cur"
    $noCur           = "$DestDir\sylveon_unavailable.cur"
    $sizeNSCur       = "$DestDir\sylveon_vertical_resize.cur"
    $sizeWECur       = "$DestDir\sylveon_horizontal_resize.cur"
    $sizeNWSECur     = "$DestDir\sylveon_diagonal_resize1.cur"
    $sizeNESWCur     = "$DestDir\sylveon_diagonal_resize2.cur"
    $sizeAllCur      = "$DestDir\sylveon_move.cur"
    $upArrowCur      = "$DestDir\sylveon_alternate.cur"
    $linkCur         = "$DestDir\sylveon_link.cur"

    Set-ItemProperty -Path $regPath -Name "(default)" -Value "Sylveon Custom"
    Set-ItemProperty -Path $regPath -Name "Arrow" -Value $arrowCur
    Set-ItemProperty -Path $regPath -Name "Help" -Value $helpCur
    Set-ItemProperty -Path $regPath -Name "AppStarting" -Value $appStartingCur
    Set-ItemProperty -Path $regPath -Name "Wait" -Value $waitAni
    Set-ItemProperty -Path $regPath -Name "Crosshair" -Value $crosshairCur
    Set-ItemProperty -Path $regPath -Name "IBeam" -Value $textCur
    Set-ItemProperty -Path $regPath -Name "NWPen" -Value $penCur
    Set-ItemProperty -Path $regPath -Name "No" -Value $noCur
    Set-ItemProperty -Path $regPath -Name "SizeNS" -Value $sizeNSCur
    Set-ItemProperty -Path $regPath -Name "SizeWE" -Value $sizeWECur
    Set-ItemProperty -Path $regPath -Name "SizeNWSE" -Value $sizeNWSECur
    Set-ItemProperty -Path $regPath -Name "SizeNESW" -Value $sizeNESWCur
    Set-ItemProperty -Path $regPath -Name "SizeAll" -Value $sizeAllCur
    Set-ItemProperty -Path $regPath -Name "UpArrow" -Value $upArrowCur
    Set-ItemProperty -Path $regPath -Name "Hand" -Value $linkCur

    $schemeStr = "$arrowCur,$helpCur,$appStartingCur,$waitAni,$crosshairCur,$textCur,$penCur,$noCur,$sizeNSCur,$sizeWECur,$sizeNWSECur,$sizeNESWCur,$sizeAllCur,$upArrowCur,$linkCur,"
    Set-ItemProperty -Path $schemesKey -Name "Sylveon Custom" -Value $schemeStr

    # Cập nhật trực tiếp con trỏ vào bộ nhớ Win32
    $cMappings = @(
        @{ Id = 32512; Path = $arrowCur },       # OCR_NORMAL
        @{ Id = 32651; Path = $helpCur },        # OCR_HELP
        @{ Id = 32650; Path = $appStartingCur },  # OCR_APPSTARTING
        @{ Id = 32514; Path = $waitAni },        # OCR_WAIT
        @{ Id = 32515; Path = $crosshairCur },   # OCR_CROSS
        @{ Id = 32516; Path = $textCur },        # OCR_IBEAM
        @{ Id = 32648; Path = $noCur },          # OCR_NO
        @{ Id = 32645; Path = $sizeNSCur },      # OCR_SIZENS
        @{ Id = 32644; Path = $sizeWECur },      # OCR_SIZEWE
        @{ Id = 32642; Path = $sizeNWSECur },    # OCR_SIZENWSE
        @{ Id = 32643; Path = $sizeNESWCur },    # OCR_SIZENESW
        @{ Id = 32646; Path = $sizeAllCur },     # OCR_SIZEALL
        @{ Id = 32513; Path = $upArrowCur },     # OCR_UP
        @{ Id = 32649; Path = $linkCur }         # OCR_HAND
    )

    foreach ($m in $cMappings) {
        $h = [LiveCursorSetter2]::LoadCursorFromFile($m.Path)
        if ($h -ne [IntPtr]::Zero) { [LiveCursorSetter2]::SetSystemCursor($h, [uint32]$m.Id) | Out-Null }
    }
}
elseif ($Scheme -eq "sylveon-paw") {
    Write-Host "🐾 Đang áp dụng con trỏ chuột Bàn Chân Sylveon Paw..." -ForegroundColor Magenta
    $DestDir = "$env:LOCALAPPDATA\Cursors\Sylveon Paw"
    if (-not (Test-Path $DestDir)) { New-Item -ItemType Directory -Path $DestDir -Force | Out-Null }
    
    $pawSource = "$PSScriptRoot\sylveon\pixel_chibi\sylveonpaw2.cur"
    $destCur = "$DestDir\sylveon_paw.cur"
    Copy-Item $pawSource $destCur -Force

    Set-ItemProperty -Path $regPath -Name "(default)" -Value "Sylveon Paw"
    Set-ItemProperty -Path $regPath -Name "Arrow" -Value $destCur
    Set-ItemProperty -Path $regPath -Name "Help" -Value $destCur
    Set-ItemProperty -Path $regPath -Name "AppStarting" -Value $destCur
    Set-ItemProperty -Path $regPath -Name "Wait" -Value $destCur
    Set-ItemProperty -Path $regPath -Name "Crosshair" -Value $destCur
    Set-ItemProperty -Path $regPath -Name "IBeam" -Value $destCur
    Set-ItemProperty -Path $regPath -Name "NWPen" -Value $destCur
    Set-ItemProperty -Path $regPath -Name "No" -Value $destCur
    Set-ItemProperty -Path $regPath -Name "SizeNS" -Value $destCur
    Set-ItemProperty -Path $regPath -Name "SizeWE" -Value $destCur
    Set-ItemProperty -Path $regPath -Name "SizeNWSE" -Value $destCur
    Set-ItemProperty -Path $regPath -Name "SizeNESW" -Value $destCur
    Set-ItemProperty -Path $regPath -Name "SizeAll" -Value $destCur
    Set-ItemProperty -Path $regPath -Name "UpArrow" -Value $destCur
    Set-ItemProperty -Path $regPath -Name "Hand" -Value $destCur

    $schemeStr = "$destCur,$destCur,$destCur,$destCur,,,$destCur,$destCur,$destCur,$destCur,$destCur,$destCur,$destCur,$destCur,$destCur,"
    Set-ItemProperty -Path $schemesKey -Name "Sylveon Paw" -Value $schemeStr

    $h = [LiveCursorSetter2]::LoadCursorFromFile($destCur)
    if ($h -ne [IntPtr]::Zero) { [LiveCursorSetter2]::SetSystemCursor($h, 32512) | Out-Null }
    $hHand = [LiveCursorSetter2]::LoadCursorFromFile($destCur)
    if ($hHand -ne [IntPtr]::Zero) { [LiveCursorSetter2]::SetSystemCursor($hHand, 32649) | Out-Null }
}
elseif ($Scheme -eq "sylveon-chibi") {
    Write-Host "🌸 Đang áp dụng con trỏ chuột Sylveon Chibi (Đơn giản - Tĩnh)..." -ForegroundColor Magenta
    $DestDir = "$env:LOCALAPPDATA\Cursors\Sylveon Simple Chibi"
    if (-not (Test-Path $DestDir)) { New-Item -ItemType Directory -Path $DestDir -Force | Out-Null }
    
    Copy-Item "$PSScriptRoot\sylveon\pixel_chibi_frame0.cur" "$DestDir\sylveon_simple_chibi.cur" -Force
    Copy-Item "$PSScriptRoot\sylveon\pixel_chibi\sylveonpaw2.cur" "$DestDir\sylveon_paw.cur" -Force
    Copy-Item "$PSScriptRoot\sylveon\pixel_chibi\text.cur" "$DestDir\sylveon_text.cur" -Force

    $chibiCur = "$DestDir\sylveon_simple_chibi.cur"
    $pawCur = "$DestDir\sylveon_paw.cur"
    $textCur = "$DestDir\sylveon_text.cur"

    Set-ItemProperty -Path $regPath -Name "(default)" -Value "Sylveon Simple Chibi"
    Set-ItemProperty -Path $regPath -Name "Arrow" -Value $chibiCur
    Set-ItemProperty -Path $regPath -Name "Help" -Value $chibiCur
    Set-ItemProperty -Path $regPath -Name "AppStarting" -Value $pawCur
    Set-ItemProperty -Path $regPath -Name "Wait" -Value $pawCur
    Set-ItemProperty -Path $regPath -Name "Crosshair" -Value $textCur
    Set-ItemProperty -Path $regPath -Name "IBeam" -Value $textCur
    Set-ItemProperty -Path $regPath -Name "NWPen" -Value $pawCur
    Set-ItemProperty -Path $regPath -Name "No" -Value $chibiCur
    Set-ItemProperty -Path $regPath -Name "SizeNS" -Value $pawCur
    Set-ItemProperty -Path $regPath -Name "SizeWE" -Value $pawCur
    Set-ItemProperty -Path $regPath -Name "SizeNWSE" -Value $pawCur
    Set-ItemProperty -Path $regPath -Name "SizeNESW" -Value $pawCur
    Set-ItemProperty -Path $regPath -Name "SizeAll" -Value $pawCur
    Set-ItemProperty -Path $regPath -Name "UpArrow" -Value $chibiCur
    Set-ItemProperty -Path $regPath -Name "Hand" -Value $pawCur

    $schemeStr = "$chibiCur,$chibiCur,$pawCur,$pawCur,$textCur,$textCur,$pawCur,$chibiCur,$pawCur,$pawCur,$pawCur,$pawCur,$pawCur,$chibiCur,$pawCur,"
    Set-ItemProperty -Path $schemesKey -Name "Sylveon Simple Chibi" -Value $schemeStr

    $h = [LiveCursorSetter2]::LoadCursorFromFile($chibiCur)
    if ($h -ne [IntPtr]::Zero) { [LiveCursorSetter2]::SetSystemCursor($h, 32512) | Out-Null }
    $hHand = [LiveCursorSetter2]::LoadCursorFromFile($pawCur)
    if ($hHand -ne [IntPtr]::Zero) { [LiveCursorSetter2]::SetSystemCursor($hHand, 32649) | Out-Null }
}
elseif ($Scheme -eq "sylveon-animated") {
    Write-Host "🎀 Đang áp dụng con trỏ chuột Sylveon Hoạt Họa (Animated)..." -ForegroundColor Magenta
    $SourceFaer = "$PSScriptRoot\sylveon\faereevee"
    $DestDir = "$env:LOCALAPPDATA\Cursors\Sylveon Cursors"
    if (-not (Test-Path $DestDir)) { New-Item -ItemType Directory -Path $DestDir -Force | Out-Null }
    Copy-Item "$SourceFaer\*" $DestDir -Force

    Set-ItemProperty -Path $regPath -Name "(default)" -Value "Sylveon Cursors"
    Set-ItemProperty -Path $regPath -Name "Arrow" -Value "$DestDir\Sylveon - Normal.ani"
    Set-ItemProperty -Path $regPath -Name "Hand" -Value "$DestDir\Sylveon - Link Select.ani"
    Set-ItemProperty -Path $regPath -Name "Wait" -Value "$DestDir\Sylveon - Working in the Background.ani"
}
elseif ($Scheme -eq "pokemon") {
    Write-Host "⚡ Đang áp dụng con trỏ chuột Pokemon Trainer..." -ForegroundColor Yellow
    $SourceDir = "$PSScriptRoot\pokemon\Pokemon-Regular-Windows"
    $DestDir = "$env:LOCALAPPDATA\Cursors\Pokemon Cursors"
    if (-not (Test-Path $DestDir)) { New-Item -ItemType Directory -Path $DestDir -Force | Out-Null }
    Copy-Item "$SourceDir\*" $DestDir -Force

    Set-ItemProperty -Path $regPath -Name "(default)" -Value "Pokemon Cursors"
    Set-ItemProperty -Path $regPath -Name "Arrow" -Value "$DestDir\Default.cur"
    Set-ItemProperty -Path $regPath -Name "Hand" -Value "$DestDir\Link.cur"
    Set-ItemProperty -Path $regPath -Name "Wait" -Value "$DestDir\Busy.ani"

    $h = [LiveCursorSetter2]::LoadCursorFromFile("$DestDir\Default.cur")
    if ($h -ne [IntPtr]::Zero) { [LiveCursorSetter2]::SetSystemCursor($h, 32512) | Out-Null }
}
elseif ($Scheme -eq "catppuccin") {
    Write-Host "🌸 Đang áp dụng con trỏ chuột Catppuccin Mocha Red..." -ForegroundColor Magenta
    $SourceDir = "$PSScriptRoot\catppuccin-mocha-red"
    $DestDir = "$env:LOCALAPPDATA\Cursors\Catppuccin Mocha Red"
    if (-not (Test-Path $DestDir)) { New-Item -ItemType Directory -Path $DestDir -Force | Out-Null }
    Copy-Item "$SourceDir\*" $DestDir -Force

    Set-ItemProperty -Path $regPath -Name "(default)" -Value "Catppuccin Mocha Red"
    Set-ItemProperty -Path $regPath -Name "Arrow" -Value "$DestDir\arrow.cur"
    Set-ItemProperty -Path $regPath -Name "Hand" -Value "$DestDir\link.cur"

    $h = [LiveCursorSetter2]::LoadCursorFromFile("$DestDir\arrow.cur")
    if ($h -ne [IntPtr]::Zero) { [LiveCursorSetter2]::SetSystemCursor($h, 32512) | Out-Null }
}
else {
    Write-Host "🔄 Đang khôi phục con trỏ chuột mặc định của Windows..." -ForegroundColor Cyan
    Set-ItemProperty -Path $regPath -Name "(default)" -Value "Windows Default"
    Set-ItemProperty -Path $regPath -Name "Arrow" -Value "$env:WINDIR\cursors\aero_arrow.cur"
    Set-ItemProperty -Path $regPath -Name "Hand" -Value "$env:WINDIR\cursors\aero_link.cur"
}

[LiveCursorSetter2]::SystemParametersInfo(0x0057, 0, [IntPtr]::Zero, 3) | Out-Null
Write-Host "✨ Cập nhật con trỏ chuột thành công!" -ForegroundColor Green
