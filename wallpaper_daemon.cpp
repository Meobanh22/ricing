#define UNICODE
#define _UNICODE
#include <windows.h>
#include <shobjidl.h>
#include <stdio.h>
#include <vector>
#include <string>
#include <algorithm>

std::wstring get_exe_dir() {
    wchar_t buffer[MAX_PATH];
    DWORD len = GetModuleFileNameW(NULL, buffer, MAX_PATH);
    if (len == 0 || len >= MAX_PATH) return L".";
    std::wstring path(buffer);
    size_t pos = path.find_last_of(L"\\/");
    return (pos != std::wstring::npos) ? path.substr(0, pos) : L".";
}

const std::wstring BASE_DIR = get_exe_dir();
const std::wstring WALLPAPER_DIR = BASE_DIR + L"\\wallpapers";
const std::wstring STATE_FILE = WALLPAPER_DIR + L"\\.current_wallpaper";
const std::wstring LOG_FILE = BASE_DIR + L"\\daemon.log";

void log_msg(const wchar_t* fmt, ...) {
    FILE* f = _wfopen(LOG_FILE.c_str(), L"a, ccs=UTF-8");
    if (!f) return;
    va_list args;
    va_start(args, fmt);
    vfwprintf(f, fmt, args);
    va_end(args);
    fwprintf(f, L"\n");
    fclose(f);
}

std::vector<std::wstring> get_wallpapers() {
    std::vector<std::wstring> list;
    WIN32_FIND_DATAW ffd;
    std::wstring search_path = WALLPAPER_DIR + L"\\*";
    HANDLE hFind = FindFirstFileW(search_path.c_str(), &ffd);

    if (hFind != INVALID_HANDLE_VALUE) {
        do {
            if (!(ffd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
                std::wstring name = ffd.cFileName;
                if (!name.empty() && name[0] != L'.') {
                    size_t dot = name.find_last_of(L'.');
                    if (dot != std::wstring::npos) {
                        std::wstring ext = name.substr(dot);
                        for (auto &c : ext) c = towlower(c);
                        if (ext == L".png" || ext == L".jpg" || ext == L".jpeg" || ext == L".bmp") {
                            list.push_back(name);
                        }
                    }
                }
            }
        } while (FindNextFileW(hFind, &ffd));
        FindClose(hFind);
    }
    std::sort(list.begin(), list.end());
    return list;
}

std::wstring get_current_wallpaper() {
    FILE* f = _wfopen(STATE_FILE.c_str(), L"r, ccs=UTF-8");
    if (!f) return L"";
    wchar_t buf[512] = {0};
    if (fgetws(buf, 510, f)) {
        size_t len = wcslen(buf);
        while (len > 0 && (buf[len-1] == L'\r' || buf[len-1] == L'\n' || buf[len-1] == L' ')) {
            buf[--len] = L'\0';
        }
    }
    fclose(f);
    return std::wstring(buf);
}

void save_current_wallpaper(const std::wstring& name) {
    FILE* f = _wfopen(STATE_FILE.c_str(), L"w, ccs=UTF-8");
    if (f) {
        fputws(name.c_str(), f);
        fclose(f);
    }
}

std::wstring switch_to_next() {
    auto files = get_wallpapers();
    if (files.empty()) return L"";

    std::wstring current = get_current_wallpaper();
    size_t next_idx = 0;
    for (size_t i = 0; i < files.size(); ++i) {
        if (files[i] == current) {
            next_idx = (i + 1) % files.size();
            break;
        }
    }

    std::wstring target_name = files[next_idx];
    std::wstring full_path = WALLPAPER_DIR + L"\\" + target_name;

    log_msg(L"Switching to: %ls (from %ls)", target_name.c_str(), current.c_str());

    IDesktopWallpaper* pWallpaper = NULL;
    HRESULT hr = CoCreateInstance(CLSID_DesktopWallpaper, NULL, CLSCTX_ALL, IID_IDesktopWallpaper, (void**)&pWallpaper);
    if (SUCCEEDED(hr) && pWallpaper) {
        pWallpaper->SetWallpaper(NULL, full_path.c_str());
        pWallpaper->Release();
    } else {
        SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, (void*)full_path.c_str(), SPIF_UPDATEINIFILE | SPIF_SENDCHANGE);
    }

    save_current_wallpaper(target_name);
    return target_name;
}

LRESULT CALLBACK WndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    if (msg == WM_HOTKEY) {
        log_msg(L"WM_HOTKEY received in WndProc! ID = %lld", (long long)wParam);
        switch_to_next();
        return 0;
    }
    return DefWindowProc(hWnd, msg, wParam, lParam);
}

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    CoInitialize(NULL);

    if (strstr(lpCmdLine, "next") != NULL) {
        if (AttachConsole(ATTACH_PARENT_PROCESS)) {
            freopen("CONOUT$", "w", stdout);
        }
        std::wstring switched = switch_to_next();
        if (!switched.empty()) {
            wprintf(L"Switched to: %ls\n", switched.c_str());
        }
        CoUninitialize();
        return 0;
    }

    // Single instance check
    HANDLE hMutex = CreateMutexA(NULL, TRUE, "SylveonWallpaperSwitcherMutex_DManh_v3");
    if (GetLastError() == ERROR_ALREADY_EXISTS) {
        switch_to_next();
        CoUninitialize();
        return 0;
    }

    log_msg(L"=== Daemon starting v3 ===");

    // Register a top-level HIDDEN window (NOT HWND_MESSAGE)
    WNDCLASSEXW wx = {0};
    wx.cbSize = sizeof(WNDCLASSEXW);
    wx.lpfnWndProc = WndProc;
    wx.hInstance = hInstance;
    wx.lpszClassName = L"SylveonTopLevelHotkeyReceiver";
    RegisterClassExW(&wx);

    // Parent is NULL -> top-level window in desktop hierarchy, guaranteed to receive WM_HOTKEY!
    HWND hWnd = CreateWindowExW(0, L"SylveonTopLevelHotkeyReceiver", L"SylveonHotkeyReceiver",
                                WS_POPUP, 0, 0, 0, 0, NULL, NULL, hInstance, NULL);

    log_msg(L"Top-level hidden window: %p", hWnd);

    // Register hotkeys with MOD_NOREPEAT (0x4000)
    UINT mod_ca = MOD_CONTROL | MOD_ALT | 0x4000;
    UINT mod_cs = MOD_CONTROL | MOD_SHIFT | 0x4000;

    // 1. Ctrl + Alt + W
    BOOL r1 = RegisterHotKey(hWnd, 1, mod_ca, 'W');
    // 2. Ctrl + Shift + W
    BOOL r2 = RegisterHotKey(hWnd, 2, mod_cs, 'W');
    // 3. Ctrl + Alt + Right Arrow (Không bao giờ đụng UniKey hay Fn!)
    BOOL r3 = RegisterHotKey(hWnd, 3, mod_ca, VK_RIGHT);
    // 4. Ctrl + Alt + Space (Phím cách to đùng, siêu dễ bấm!)
    BOOL r4 = RegisterHotKey(hWnd, 4, mod_ca, VK_SPACE);
    // 5. F8
    BOOL r5 = RegisterHotKey(hWnd, 5, 0x4000, VK_F8);

    log_msg(L"Hotkeys registered: CA+W=%d, CS+W=%d, CA+Right=%d, CA+Space=%d, F8=%d", r1, r2, r3, r4, r5);

    MSG msg;
    while (GetMessage(&msg, NULL, 0, 0) > 0) {
        if (msg.message == WM_HOTKEY) {
            log_msg(L"WM_HOTKEY in message loop! ID = %lld", (long long)msg.wParam);
            switch_to_next();
        }
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }

    for (int i = 1; i <= 5; ++i) UnregisterHotKey(hWnd, i);
    DestroyWindow(hWnd);
    CloseHandle(hMutex);
    CoUninitialize();
    return 0;
}

