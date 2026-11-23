# Original character restoration

The final character colors and linework are copied from `../serena_fennekin_original.jpg`. The native layer is 1376 × 768 and is resized once to the wallpaper canvas, 1678 × 937.

`character_extraction_guide.png` is a built-in image_gen cutout used only to guide segmentation. Its generated character RGB is not used in the restored wallpaper. The matte is refined against the source's original dark contours; antialiased edge pixels are blended during compositing.

`sunset_background_plate.png` is a built-in image_gen background plate. It fills only the previous character silhouette. `sunset_before_character_restore.png` preserves the approved wallpaper before restoration. Visible background outside the replacement area stays unchanged.

Run `perl dev_tools/wallpaper_generator/restore_original_characters.pl` from the repository root to rebuild the foreground and background layers and update `assets/wallpapers/serena_fennekin_wallpaper_grass_fixed.png`. This command does not install or apply the wallpaper. Use `--output /tmp/serena_wallpaper.png` to render a separate copy.

Intermediate masks and the native foreground layer are created in a temporary directory and removed automatically. Old previews, comparisons and redundant backups are not needed to rebuild the final wallpaper.

Validation on 2026-11-19:

- All 344,527 fully opaque native character pixels match the decoded original RGB exactly.
- All 1,037,807 background pixels outside the replacement area match the approved wallpaper exactly.
- Foreground details and edges were visually compared with the original, including eyes, nose, fingers, ribbon, tail and toes.
- The installed desktop and lock-screen files match the restored wallpaper.

Successful generation prompts are in [restoration_prompts.txt](restoration_prompts.txt).

For future background edits, edit the background layer separately and composite `original_character_layer_wallpaper.png` over it. Keep the source foreground layer intact.
