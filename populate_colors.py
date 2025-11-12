"""
Populate Colors Script

Analyzes all cached wallpapers and extracts their dominant colors.
Run this once to populate color data for existing wallpapers.
"""

import os
import sys

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

from cache_manager import CacheManager
from color_analyzer import ColorAnalyzer
from config import CacheSettings


def populate_colors():
    """Analyze all cached wallpapers and add color metadata"""
    # Get cache directory from config, use default if empty
    cache_dir = CacheSettings.get("directory", "")
    if not cache_dir:
        # Use default location in user's home directory
        cache_dir = os.path.join(os.path.expanduser("~"), "WallpaperChangerCache")
    else:
        cache_dir = os.path.expanduser(cache_dir)

    cache_manager = CacheManager(
        directory=cache_dir,
        max_items=CacheSettings.get("max_items", 50),
        enable_rotation=CacheSettings.get("enable_rotation", True)
    )

    print(f"Cache directory: {cache_manager.cache_dir}")

    print("=" * 60)
    print("  Wallpaper Color Population Tool")
    print("=" * 60)
    print()

    # Get all cache entries
    entries = cache_manager._index.get("items", [])
    total = len(entries)

    if total == 0:
        print("No wallpapers found in cache.")
        return

    print(f"Found {total} wallpapers to analyze...")
    print()

    updated_count = 0
    skipped_count = 0
    error_count = 0

    for i, entry in enumerate(entries, 1):
        image_path = entry.get("path")

        # Skip if already has color data
        if "color_categories" in entry and entry["color_categories"]:
            skipped_count += 1
            print(f"[{i}/{total}] SKIP: {os.path.basename(image_path)} (already analyzed)")
            continue

        if not os.path.exists(image_path):
            error_count += 1
            print(f"[{i}/{total}] ERROR: {os.path.basename(image_path)} (file not found)")
            continue

        try:
            # Extract colors
            print(f"[{i}/{total}] Analyzing: {os.path.basename(image_path)}...", end=" ")

            color_categories = ColorAnalyzer.get_color_categories(image_path, num_colors=3)
            primary_color = ColorAnalyzer.get_primary_color_category(image_path)

            # Update entry
            entry["color_categories"] = color_categories
            entry["primary_color"] = primary_color

            updated_count += 1
            print(f"OK - Colors: {', '.join(color_categories) if color_categories else 'none'}")

        except Exception as e:
            error_count += 1
            print(f"ERROR: {e}")

    # Save updated cache
    if updated_count > 0:
        print()
        print("Saving updated cache...")
        cache_manager._save()
        print("Done!")

    # Print summary
    print()
    print("=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"Total wallpapers:  {total}")
    print(f"Updated:           {updated_count}")
    print(f"Skipped:           {skipped_count}")
    print(f"Errors:            {error_count}")
    print()

    if updated_count > 0:
        print("Color data has been populated!")
        print("Restart the GUI to see the color filter options.")
    else:
        print("No wallpapers needed color analysis.")


if __name__ == "__main__":
    try:
        populate_colors()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
