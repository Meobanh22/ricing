# 1. Restore the EXACT untouched original serena_fennekin_ascii_sakura.png
$dest = "$PSScriptRoot\wallpapers\serena_fennekin_ascii_sakura.png"

# 2. Set as active wallpaper immediately
& "$PSScriptRoot\wallpaper_switcher.exe" next
# Update .current_wallpaper to serena_fennekin_ascii_sakura.png
Set-Content -Path "$PSScriptRoot\wallpapers\.current_wallpaper" -Value 'serena_fennekin_ascii_sakura.png' -Encoding UTF8

# Call C++ switcher with specific path via Windows API to apply immediately
$code = @'
using System;
using System.Runtime.InteropServices;
public class Wall {
    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
    public static void Set(string path) {
        SystemParametersInfo(20, 0, path, 3);
    }
}
'@
Add-Type -TypeDefinition $code
[Wall]::Set((Resolve-Path $dest).Path)
Write-Output "Applied exact original ASCII wallpaper to desktop!"

