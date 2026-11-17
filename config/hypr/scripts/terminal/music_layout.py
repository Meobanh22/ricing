"""Shared lyric and waveform regions, independent of lyric availability."""


def visualizer_regions(rows):
    rows = max(0, rows)
    lyric_rows = min(10, max(4, rows // 2), max(0, rows - 1))
    lyric_top = max(0, (rows - lyric_rows) // 2)
    spectrum_top = min(max(0, rows - 1), lyric_top + lyric_rows + 1)
    return lyric_top, lyric_rows, spectrum_top
