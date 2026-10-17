-- ==============================================================================
-- 🌹 SERENA & SYLVEON HYPRLAND CONFIGURATION (v0.56+ / v0.57+ LUA NATIVE)
-- ==============================================================================
-- Chủ đề: Pokémon Serena & Sylveon
-- Tông màu: Serena Crimson (#E53935), Ribbon Rose (#FF6B8B), Midnight Charcoal (#181825)
-- Hiển thị: Scale 1.2 (120%) chuẩn tỷ lệ điểm ảnh 1600x900 sắc nét
-- ==============================================================================

------------------
---- MONITORS ----
------------------
-- Scale 1.2 (120%) chuẩn tỷ lệ pixel 1600x900 sắc nét cho màn hình 14 inch Full HD
hl.monitor({
    output   = "eDP-1",
    mode     = "preferred",
    position = "auto",
    scale    = "1.2",
})
hl.monitor({
    output   = "",
    mode     = "preferred",
    position = "auto",
    scale    = "1.2",
})

-------------------------------
---- ENVIRONMENT VARIABLES ----
-------------------------------
hl.env("XDG_CURRENT_DESKTOP", "Hyprland")
hl.env("XDG_SESSION_TYPE", "wayland")
hl.env("XDG_SESSION_DESKTOP", "Hyprland")
hl.env("GDK_BACKEND", "wayland,x11,*")
hl.env("QT_QPA_PLATFORM", "wayland;xcb")

-- Bộ gõ Tiếng Việt (Fcitx5 Native Wayland chuẩn mượt)
hl.env("GTK_IM_MODULE", "fcitx")
hl.env("QT_IM_MODULE", "fcitx")
hl.env("XMODIFIERS", "@im=fcitx")
hl.env("SDL_IM_MODULE", "fcitx")
hl.env("GLFW_IM_MODULE", "fcitx")

-- Con trỏ chuột Sylveon Custom
hl.env("HYPRCURSOR_THEME", "sylveon-custom")
hl.env("HYPRCURSOR_SIZE", "24")
hl.env("XCURSOR_THEME", "sylveon-custom")
hl.env("XCURSOR_SIZE", "24")

-------------------
---- AUTOSTART ----
-------------------
hl.on("hyprland.start", function ()
    -- 1. Quản lý hình nền siêu mượt
    hl.exec_cmd("swww-daemon &")
    hl.exec_cmd("sleep 0.8 && python3 ~/.config/hypr/scripts/wallpaper_switcher.py current")

    -- 2. Thanh Bar & Tiện ích (Waybar)
    hl.exec_cmd("waybar")

    -- 3. Con trỏ chuột Sylveon Custom
    hl.exec_cmd("hyprctl setcursor sylveon-custom 24")
    hl.exec_cmd("gsettings set org.gnome.desktop.interface cursor-theme 'sylveon-custom'")

    -- 4. Polkit xác thực quyền (Root/Admin popup)
    hl.exec_cmd("/usr/lib/policykit-1-gnome/polkit-gnome-authentication-agent-1 || /usr/libexec/polkit-gnome-authentication-agent-1")

    -- 5. Kích hoạt bộ gõ Tiếng Việt Fcitx5 (hoặc IBus fallback)
    hl.exec_cmd("(fcitx5 -d --replace || ~/.config/hypr/scripts/init_ime.sh)")

    -- 6. Trung tâm thông báo (SwayNC)
    hl.exec_cmd("swaync &")

    -- 7. Khởi động Dịch vụ lưu trữ mật khẩu & mã hóa (GNOME Keyring)
    hl.exec_cmd("gnome-keyring-daemon --start --components=secrets,pkcs11,ssh")
    hl.exec_cmd("dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP GNOME_KEYRING_CONTROL SSH_AUTH_SOCK")
end)

-----------------------
---- INPUT & TOUCH ----
-----------------------
hl.config({
    input = {
        kb_layout = "us",
        follow_mouse = 1,
        touchpad = {
            natural_scroll = true,
            tap_to_click = true,
            scroll_factor = 0.8,
        },
        sensitivity = 0,
    },
    cursor = {
        no_hardware_cursors = true,
        enable_hyprcursor = true,
        sync_gsettings_theme = true,
    },
})

-----------------------
---- LOOK AND FEEL ----
-----------------------
hl.config({
    general = {
        gaps_in  = 6,
        gaps_out = 12,
        border_size = 2,

        col = {
            active_border   = { colors = { "rgb(E53935)", "rgb(FF6B8B)" }, angle = 45 },
            inactive_border = "rgba(24182588)",
        },

        layout = "dwindle",
        allow_tearing = false,
    },

    decoration = {
        rounding = 14,

        active_opacity     = 0.94,
        inactive_opacity   = 0.85,
        fullscreen_opacity = 1.0,

        blur = {
            enabled           = true,
            size              = 6,
            passes            = 3,
            new_optimizations = true,
            ignore_opacity    = true,
            xray              = false,
        },

        shadow = {
            enabled        = true,
            range          = 22,
            render_power   = 3,
            color          = "rgba(00000055)",
            color_inactive = "rgba(00000033)",
        },
    },

    animations = {
        enabled = true,
    },
})

--------------------
---- ANIMATIONS ----
--------------------
hl.curve("wind",       { type = "bezier", points = { {0.05, 0.9},  {0.1, 1.05} } })
hl.curve("winIn",      { type = "bezier", points = { {0.1, 1.1},   {0.1, 1.1}  } })
hl.curve("winOut",     { type = "bezier", points = { {0.3, -0.3},  {0, 1}      } })
hl.curve("bounce",     { type = "bezier", points = { {0.34, 1.56}, {0.64, 1}   } })
hl.curve("menu_decel", { type = "bezier", points = { {0.1, 1},     {0, 1}      } })
hl.curve("menu_accel", { type = "bezier", points = { {0.38, 0.04}, {1, 0.07}   } })

hl.animation({ leaf = "windows",     enabled = true, speed = 4,  bezier = "wind",    style = "slide" })
hl.animation({ leaf = "windowsIn",   enabled = true, speed = 4,  bezier = "winIn",   style = "popin 75%" })
hl.animation({ leaf = "windowsOut",  enabled = true, speed = 4,  bezier = "winOut",  style = "popin 75%" })
hl.animation({ leaf = "border",      enabled = true, speed = 8,  bezier = "default" })
hl.animation({ leaf = "borderangle", enabled = true, speed = 30, bezier = "default", style = "loop" })
hl.animation({ leaf = "fade",        enabled = true, speed = 4,  bezier = "default" })
hl.animation({ leaf = "workspaces",  enabled = true, speed = 5,  bezier = "wind",    style = "slide" })
hl.animation({ leaf = "layersIn",    enabled = true, speed = 2,  bezier = "default", style = "fade" })
hl.animation({ leaf = "layersOut",   enabled = true, speed = 2,  bezier = "default", style = "fade" })

----------------------
---- WINDOW RULES ----
----------------------
hl.window_rule({
    name = "suppress-maximize",
    match = { class = ".*" },
    suppress_event = "maximize",
})

hl.window_rule({
    name = "float-settings",
    match = { class = "^(pavucontrol|nm-connection-editor|blueman-manager)$" },
    float = true,
})

hl.window_rule({
    name = "btop-serena-rule",
    match = { class = "^(btop-serena)$" },
    float = true,
    size = "960 620",
    center = true,
})

hl.window_rule({
    name = "serena-dashboard-rule",
    match = { class = "^(serena-dashboard)$" },
    float = true,
    animation = "slide top",
})

hl.window_rule({
    name = "dialogs-rule",
    match = { title = "^(Open File|Save File|Confirm).*" },
    float = true,
})

---------------------
---- LAYER RULES ----
---------------------
hl.layer_rule({
    name = "rofi-blur",
    match = { namespace = "rofi" },
    blur = true,
})

---------------------
---- KEYBINDINGS ----
---------------------
local mainMod = "SUPER"

-- Ứng dụng thường dùng
hl.bind(mainMod .. " + RETURN", hl.dsp.exec_cmd("kitty || gnome-terminal"))
hl.bind(mainMod .. " + SPACE",  hl.dsp.exec_cmd("~/.config/hypr/scripts/OpenApps.sh"))
hl.bind(mainMod .. " + E",      hl.dsp.exec_cmd("thunar || nautilus"))
hl.bind(mainMod .. " + B",      hl.dsp.exec_cmd("firefox || google-chrome || brave-browser"))

-- Quản lý cửa sổ
hl.bind(mainMod .. " + Q", hl.dsp.window.close())
hl.bind(mainMod .. " + V", hl.dsp.window.float({ action = "toggle" }))
hl.bind(mainMod .. " + F", function() hl.dispatch("fullscreen", "0") end)

-- Bảng điều khiển & Tiện ích mở rộng
hl.bind(mainMod .. " + ESCAPE",         hl.dsp.exec_cmd("~/.config/hypr/scripts/Wlogout.sh"))
hl.bind(mainMod .. " + S",              hl.dsp.exec_cmd("python3 ~/.config/hypr/scripts/serena_dashboard.py"))
hl.bind(mainMod .. " + N",              hl.dsp.exec_cmd("~/.config/hypr/scripts/toggle_control_center.sh"))
hl.bind("CTRL + SHIFT + ESCAPE",        hl.dsp.exec_cmd("kitty --class btop-serena -T 'Task Manager' btop"))

-- Tiện ích hệ thống
hl.bind(mainMod .. " + L",         hl.dsp.exec_cmd("hyprlock"))
hl.bind("Print",                   hl.dsp.exec_cmd("~/.config/hypr/scripts/screenshot.sh area"))
hl.bind(mainMod .. " + SHIFT + S", hl.dsp.exec_cmd("~/.config/hypr/scripts/screenshot.sh area"))
hl.bind("CTRL + SPACE",            hl.dsp.exec_cmd("fcitx5-remote -t || ~/.config/hypr/scripts/toggle_vietnamese.sh"))
hl.bind(mainMod .. " + W",         hl.dsp.exec_cmd("python3 ~/.config/hypr/scripts/wallpaper_switcher.py next"))

-- Phím đa phương tiện (Volume & Brightness)
hl.bind("XF86AudioRaiseVolume",  hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+"),   { locked = true, repeating = true })
hl.bind("XF86AudioLowerVolume",  hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"),   { locked = true, repeating = true })
hl.bind("XF86AudioMute",         hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"),  { locked = true })
hl.bind("XF86MonBrightnessUp",   hl.dsp.exec_cmd("brightnessctl set 5%+"),                       { locked = true, repeating = true })
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl set 5%-"),                       { locked = true, repeating = true })

-- Di chuyển tiêu điểm cửa sổ (Focus)
hl.bind(mainMod .. " + left",  hl.dsp.focus({ direction = "left" }))
hl.bind(mainMod .. " + right", hl.dsp.focus({ direction = "right" }))
hl.bind(mainMod .. " + up",    hl.dsp.focus({ direction = "up" }))
hl.bind(mainMod .. " + down",  hl.dsp.focus({ direction = "down" }))

-- Chuyển không gian làm việc (Workspaces 1 -> 5)
for i = 1, 5 do
    hl.bind(mainMod .. " + " .. i,           hl.dsp.focus({ workspace = i }))
    hl.bind(mainMod .. " + SHIFT + " .. i,   hl.dsp.window.move({ workspace = i }))
end

-- Kéo thả di chuyển & chỉnh kích thước bằng chuột
hl.bind(mainMod .. " + mouse:272", hl.dsp.window.drag(),   { mouse = true })
hl.bind(mainMod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })
