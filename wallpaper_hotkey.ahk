#Requires AutoHotkey v2.0
#SingleInstance Force
Persistent(true)

; ==============================================================================
; 🌸 Instant Wallpaper Switcher (AutoHotkey v2)
; ==============================================================================

SwitchWallpaper() {
    Run('"' . A_ScriptDir . '\wallpaper_switcher.exe" next', , "Hide")
    ToolTip("🌸 Wallpaper Switched!")
    SetTimer(() => ToolTip(), -1000)
}

^!Space::SwitchWallpaper()
^!Right::SwitchWallpaper()
^!w::SwitchWallpaper()
#!w::SwitchWallpaper()
F8::SwitchWallpaper()
