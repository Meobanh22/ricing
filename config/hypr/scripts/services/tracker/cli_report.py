#!/usr/bin/env python3
# tracker/cli_report.py — Terminal dashboard and usage charts for app_tracker.

import shutil

from tracker.utils import (
    CLR_ACCENT,
    CLR_BOLD,
    CLR_CYAN,
    CLR_MUTED,
    CLR_RESET,
    CLR_SECONDARY,
    CLR_SUCCESS,
    CLR_TEXT,
    PALETTE_COLORS,
    clean_app_name,
    clean_window_title,
    format_duration,
    make_hyperlink,
)


def get_term_layout():
    """Dynamically determine terminal dimensions and column widths to fit terminal frame."""
    cols, lines = shutil.get_terminal_size((80, 24))
    w = max(cols - 2, 58)
    app_w = min(22, max(14, int(w * 0.22)))
    bar_w = max(12, w - (app_w + 23) - 4)
    web_bar_w = min(22, max(10, int(w * 0.22)))
    web_title_w = max(24, w - web_bar_w - 22)
    return w, lines, app_w, bar_w, web_title_w, web_bar_w


def draw_stacked_distribution(items: list, width: int = 50) -> tuple:
    """Draw a continuous horizontal distribution bar with a colored legend."""
    total = sum(x[1] for x in items)
    if total <= 0:
        return f"[{'░' * width}]", ""

    segments = []
    allocated = 0
    legend_parts = []

    for i, (name, dur) in enumerate(items):
        clr = PALETTE_COLORS[i % len(PALETTE_COLORS)]
        pct = (dur / total) * 100.0
        seg_len = int(round((dur / total) * width))
        segments.append((name, dur, seg_len, clr))
        allocated += seg_len
        legend_parts.append(f"{clr}■{CLR_RESET} {name} ({pct:.1f}%)")

    diff = width - allocated
    if segments:
        name, dur, seg_len, clr = segments[0]
        segments[0] = (name, dur, max(0, seg_len + diff), clr)

    bar_str = "["
    for _, _, seg_len, clr in segments:
        if seg_len > 0:
            bar_str += f"{clr}{'█' * seg_len}"
    bar_str += f"{CLR_RESET}]"

    legend_str = "   ".join(legend_parts[:4])
    return bar_str, legend_str


def aggregate_apps(raw_stats: list) -> list:
    """Group apps by their friendly display name to prevent duplicates (e.g. code vs com.microsoft.VSCode)."""
    agg = {}
    for app_class, duration in raw_stats:
        name = clean_app_name(app_class)
        agg[name] = agg.get(name, 0.0) + duration
    return sorted(agg.items(), key=lambda x: x[1], reverse=True)


def print_combined_dashboard(title: str, app_stats: list, web_stats: list = None, total_uptime: float = None):
    w, lines, app_w, bar_w, web_title_w, web_bar_w = get_term_layout()

    print()
    print(f"{CLR_ACCENT}┌{'─' * (w - 2)}┐{CLR_RESET}")
    print(f"{CLR_ACCENT}│{CLR_RESET}  {CLR_BOLD}{CLR_TEXT}{title.center(w - 6)}{CLR_RESET}  {CLR_ACCENT}│{CLR_RESET}")
    print(f"{CLR_ACCENT}└{'─' * (w - 2)}┘{CLR_RESET}")

    grouped_apps = aggregate_apps(app_stats)
    total_tracked = sum(s[1] for s in grouped_apps)

    if total_uptime and total_uptime > 0:
        idle_time = max(0.0, total_uptime - total_tracked)
        tracked_pct = (total_tracked / total_uptime) * 100.0 if total_uptime > 0 else 0.0
        idle_pct = (idle_time / total_uptime) * 100.0 if total_uptime > 0 else 0.0
        print(f"  {CLR_CYAN}🖥  System Uptime:{CLR_RESET}     {CLR_BOLD}{format_duration(total_uptime)}{CLR_RESET}")
        print(f"  {CLR_SUCCESS}📊 Active Apps:{CLR_RESET}       {CLR_BOLD}{format_duration(total_tracked)}{CLR_RESET} ({tracked_pct:.1f}% of total uptime)")
        print(f"  {CLR_MUTED}💤 Idle / Desktop:{CLR_RESET}    {CLR_BOLD}{format_duration(idle_time)}{CLR_RESET} ({idle_pct:.1f}%)")
    else:
        print(f"  {CLR_SUCCESS}📊 Total App Time:{CLR_RESET}    {CLR_BOLD}{format_duration(total_tracked)}{CLR_RESET}")

    print()
    if not grouped_apps:
        print(f"  {CLR_MUTED}No application activity recorded yet.{CLR_RESET}")
        print(f"  {CLR_MUTED}Ensure the daemon is running: {CLR_TEXT}apptime start{CLR_RESET}\n")
        return

    stacked_width = max(16, w - 8)
    stacked_bar, legend = draw_stacked_distribution(grouped_apps, width=stacked_width)
    print(f"  {CLR_BOLD}{CLR_TEXT}📈 USAGE DISTRIBUTION (ROW OVERVIEW){CLR_RESET}")
    print(f"  {stacked_bar}")
    if legend:
        print(f"  {CLR_MUTED}{legend}{CLR_RESET}")
    print()

    print(f"  {CLR_BOLD}{CLR_TEXT}📱 DESKTOP APPLICATIONS (ROW CHART){CLR_RESET}")
    print(f"  {CLR_MUTED}{'APPLICATION':<{app_w}} {'TIME':<9} {'USAGE CHART':<{bar_w + 2}}  {'SHARE'}{CLR_RESET}")
    print(f"  {CLR_MUTED}{'─' * (w - 4)}{CLR_RESET}")

    base_time = total_tracked if total_tracked > 0 else 1.0

    for i, (friendly_name, duration) in enumerate(grouped_apps, start=0):
        pct = (duration / base_time) * 100.0
        row_clr = PALETTE_COLORS[i % len(PALETTE_COLORS)]
        filled_len = int(round(bar_w * (pct / 100.0)))
        filled_len = max(0, min(bar_w, filled_len))
        empty_len = bar_w - filled_len
        bar = f"{row_clr}{'█' * filled_len}{CLR_MUTED}{'░' * empty_len}{CLR_RESET}"
        time_str = format_duration(duration)

        print(f"  {CLR_BOLD}{CLR_TEXT}{friendly_name[:app_w]:<{app_w}}{CLR_RESET} {CLR_CYAN}{time_str:<8}{CLR_RESET} │{bar}│  {CLR_SECONDARY}{pct:>5.1f}%{CLR_RESET}")

    if web_stats:
        total_web_time = sum(item[2] for item in web_stats)
        base_web = total_web_time if total_web_time > 0 else 1.0
        print()
        print(f"  {CLR_BOLD}{CLR_TEXT}🌐 TOP WEBSITES & LINKS (ROW CHART · CLICK TO OPEN){CLR_RESET}")
        print(f"  {CLR_MUTED}{'WEBSITE / DOMAIN':<{web_title_w}} {'TIME':<9} {'USAGE CHART':<{web_bar_w + 2}}  {'SHARE'}{CLR_RESET}")
        print(f"  {CLR_MUTED}{'─' * (w - 4)}{CLR_RESET}")

        for j, (app_cls, clean_title, duration, url, domain) in enumerate(web_stats, start=0):
            if domain:
                display_label = f"{clean_title[:web_title_w - len(domain) - 4]} ({domain})"
            else:
                display_label = clean_title[:web_title_w - 2]

            pct = (duration / base_web) * 100.0
            row_clr = PALETTE_COLORS[j % len(PALETTE_COLORS)]
            filled_len = int(round(web_bar_w * (pct / 100.0)))
            filled_len = max(0, min(web_bar_w, filled_len))
            empty_len = web_bar_w - filled_len
            bar = f"{row_clr}{'█' * filled_len}{CLR_MUTED}{'░' * empty_len}{CLR_RESET}"
            time_str = format_duration(duration)

            padded_label = f"{display_label:<{web_title_w}}"
            if url:
                clickable_title = make_hyperlink(url, f"{CLR_TEXT}{padded_label}{CLR_RESET}")
            else:
                clickable_title = f"{CLR_TEXT}{padded_label}{CLR_RESET}"

            print(f"  {clickable_title} {CLR_CYAN}{time_str:<8}{CLR_RESET} │{bar}│  {CLR_SECONDARY}{pct:>5.1f}%{CLR_RESET}")

    print(f"  {CLR_MUTED}{'─' * (w - 4)}{CLR_RESET}")
    print(f"  {CLR_MUTED}💡 Commands: {CLR_TEXT}apptime web{CLR_MUTED} (all links) | {CLR_TEXT}apptime details <app>{CLR_MUTED} | {CLR_TEXT}apptime live{CLR_RESET}\n")


def print_app_details(app_name: str, details: list):
    w, lines, app_w, bar_w, web_title_w, web_bar_w = get_term_layout()
    title_w = max(24, int(w * 0.40))
    url_w = max(22, w - title_w - 18)

    print()
    print(f"{CLR_ACCENT}┌{'─' * (w - 2)}┐{CLR_RESET}")
    title_str = f"APPLICATION DETAILS: {clean_app_name(app_name).upper()}"
    print(f"{CLR_ACCENT}│{CLR_RESET}  {CLR_BOLD}{CLR_TEXT}{title_str.center(w - 6)}{CLR_RESET}  {CLR_ACCENT}│{CLR_RESET}")
    print(f"{CLR_ACCENT}└{'─' * (w - 2)}┘{CLR_RESET}")

    if not details:
        print(f"\n  {CLR_MUTED}No detailed history found for: {CLR_TEXT}{app_name}{CLR_RESET}\n")
        return

    total_time = sum(d[1] for d in details)
    print(f"  {CLR_SUCCESS}📊 Total Tracked Time:{CLR_RESET} {CLR_BOLD}{format_duration(total_time)}{CLR_RESET}\n")

    print(f"  {CLR_MUTED}{'#':<3} {'WINDOW TITLE / WEBPAGE':<{title_w}} {'LINK / URL':<{url_w}} {'TIME'}{CLR_RESET}")
    print(f"  {CLR_MUTED}{'─' * (w - 4)}{CLR_RESET}")

    for i, (title, duration, url) in enumerate(details, start=1):
        clean_title = clean_window_title(title, app_name) or "(Untitled Window)"
        clean_title = clean_title[:title_w - 2]
        time_str = format_duration(duration)

        clean_url = url if url else "-"
        clean_url_disp = clean_url[:url_w - 2]

        padded_t = f"{clean_title:<{title_w}}"
        if url:
            click_t = make_hyperlink(url, f"{CLR_TEXT}{padded_t}{CLR_RESET}")
            click_u = make_hyperlink(url, f"{CLR_CYAN}{clean_url_disp:<{url_w}}{CLR_RESET}")
        else:
            click_t = f"{CLR_TEXT}{padded_t}{CLR_RESET}"
            click_u = f"{CLR_MUTED}{clean_url_disp:<{url_w}}{CLR_RESET}"

        print(f"  {CLR_MUTED}{i:<3}{CLR_RESET} {click_t} {click_u} {CLR_CYAN}{time_str}{CLR_RESET}")

    print(f"  {CLR_MUTED}{'─' * (w - 4)}{CLR_RESET}\n")


def print_all_web_pages(web_stats: list):
    w, lines, app_w, bar_w, web_title_w, web_bar_w = get_term_layout()
    title_w = max(24, int(w * 0.40))
    url_w = max(22, w - title_w - 18)

    print()
    print(f"{CLR_ACCENT}┌{'─' * (w - 2)}┐{CLR_RESET}")
    title_str = "WEB BROWSING HISTORY (CURRENT SESSION)"
    print(f"{CLR_ACCENT}│{CLR_RESET}  {CLR_BOLD}{CLR_TEXT}{title_str.center(w - 6)}{CLR_RESET}  {CLR_ACCENT}│{CLR_RESET}")
    print(f"{CLR_ACCENT}└{'─' * (w - 2)}┘{CLR_RESET}")

    if not web_stats:
        print(f"\n  {CLR_MUTED}No web browsing activity recorded yet.{CLR_RESET}\n")
        return

    total_web_time = sum(item[2] for item in web_stats)
    print(f"  {CLR_SUCCESS}📊 Total Browsing Time:{CLR_RESET} {CLR_BOLD}{format_duration(total_web_time)}{CLR_RESET}\n")

    print(f"  {CLR_MUTED}{'#':<3} {'WEBSITE / TAB TITLE':<{title_w}} {'LINK / DOMAIN':<{url_w}} {'TIME'}{CLR_RESET}")
    print(f"  {CLR_MUTED}{'─' * (w - 4)}{CLR_RESET}")

    for i, (app_cls, title, duration, url, domain) in enumerate(web_stats, start=1):
        clean_t = title[:title_w - 2]
        time_str = format_duration(duration)

        link_disp = domain if domain else (url[:url_w - 2] if url else "-")
        link_disp = link_disp[:url_w - 2]

        padded_t = f"{clean_t:<{title_w}}"
        if url:
            click_t = make_hyperlink(url, f"{CLR_TEXT}{padded_t}{CLR_RESET}")
            click_u = make_hyperlink(url, f"{CLR_CYAN}{link_disp:<{url_w}}{CLR_RESET}")
        else:
            click_t = f"{CLR_TEXT}{padded_t}{CLR_RESET}"
            click_u = f"{CLR_MUTED}{link_disp:<{url_w}}{CLR_RESET}"

        print(f"  {CLR_MUTED}{i:<3}{CLR_RESET} {click_t} {click_u} {CLR_CYAN}{time_str}{CLR_RESET}")

    print(f"  {CLR_MUTED}{'─' * (w - 4)}{CLR_RESET}\n")
