// user.js — Firefox user preferences for Serena Wine theme.
// NOTE: Automatically applied on Firefox startup.

// 1. Enable custom stylesheets (userChrome.css & userContent.css)
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);

// 2. Enable @-moz-document in userContent.css for styling about:newtab and internal pages
user_pref("layout.css.moz-document.content.enabled", true);

// 3. Enable SVG context properties for custom colors in toolbar icons
user_pref("svg.context-properties.content.enabled", true);

// 4. Reset active theme to default dark base so userChrome can style everything cleanly
user_pref("extensions.activeThemeID", "default-theme@mozilla.org");
user_pref("layout.css.prefers-color-scheme.content-override", 0);
user_pref("ui.systemUsesDarkTheme", 1);

// 5. Clean window frame & titlebar
user_pref("browser.tabs.drawInTitlebar", true);
user_pref("browser.uidensity", 0);

// 6. Smooth scrolling & animations
user_pref("general.smoothScroll", true);

// 7. GPU Hardware Acceleration & Performance (Intel Iris Xe / Wayland)
user_pref("gfx.webrender.all", true);
user_pref("gfx.webrender.compositor", true);
user_pref("gfx.canvas.accelerated", true);
user_pref("gfx.canvas.accelerated.force-enabled", true);
user_pref("media.ffmpeg.vaapi.enabled", true);
user_pref("media.rdd-ffmpeg.enabled", true);
user_pref("widget.dmabuf.wayland_drm_backend.enabled", true);

// 8. Background tab throttling & power efficiency
user_pref("dom.timeout.enable_budget_timer_throttling", true);
user_pref("dom.ipc.processPriorityManager.enabled", true);

// 9. Memory management & background tab unloading (reduces RAM usage)
user_pref("browser.tabs.unloadOnLowMemory", true);
user_pref("browser.low_commit_space_threshold_mb", 1024);
user_pref("browser.cache.memory.capacity", 65536);

