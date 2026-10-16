# ==============================================================================
# ⏳ Preview Wait Cursor Live (Tạm thời biến con trỏ chính thành Wait trong 10 giây)
# ==============================================================================
param(
    [int]$Seconds = 12
)

$DestDir = "$env:LOCALAPPDATA\Cursors\Sylveon Custom"
$waitAni = "$DestDir\sylveon_wait.ani"
$arrowCur = "$DestDir\sylveon_arrow.cur"

$code = @"
using System;
using System.Runtime.InteropServices;
public class LivePreviewSetter {
    [DllImport("user32.dll", EntryPoint = "LoadCursorFromFileW", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern IntPtr LoadCursorFromFile(string path);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool SetSystemCursor(IntPtr hcur, uint id);
}
"@
if (-not ([System.Management.Automation.PSTypeName]'LivePreviewSetter').Type) {
    Add-Type -TypeDefinition $code
}

Write-Host "✨ Đang gán con trỏ Wait thành con trỏ chuột chính trong $Seconds giây..." -ForegroundColor Magenta
Write-Host "👉 Bạn hãy di chuột khắp màn hình để ngắm dải ruy băng uốn lượn nhé!" -ForegroundColor Yellow

$hWait = [LivePreviewSetter]::LoadCursorFromFile($waitAni)
[LivePreviewSetter]::SetSystemCursor($hWait, 32512) | Out-Null

for ($i = $Seconds; $i -gt 0; $i--) {
    Write-Host -NoNewline "`r⏳ Còn lại $i giây...  "
    Start-Sleep -Seconds 1
}
Write-Host ""

Write-Host "🎀 Đang trả lại con trỏ mũi tên Sylveon..." -ForegroundColor Cyan
$hArrow = [LivePreviewSetter]::LoadCursorFromFile($arrowCur)
[LivePreviewSetter]::SetSystemCursor($hArrow, 32512) | Out-Null

Write-Host "✨ Đã khôi phục trạng thái bình thường thành công!" -ForegroundColor Green

