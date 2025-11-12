"""
Find Duplicates Script

Scans existing wallpapers in the cache and finds duplicates or similar images.
Also populates perceptual_hash field for existing wallpapers.
"""

import os
import sys

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

from cache_manager import CacheManager
from duplicate_detector import DuplicateDetector
from config import CacheSettings


def find_and_populate_duplicates():
    """Find duplicates and populate perceptual hashes"""
    # Get cache directory from config
    cache_dir = CacheSettings.get("directory", "")
    if not cache_dir:
        cache_dir = os.path.join(os.path.expanduser("~"), "WallpaperChangerCache")
    else:
        cache_dir = os.path.expanduser(cache_dir)

    cache_manager = CacheManager(
        directory=cache_dir,
        max_items=CacheSettings.get("max_items", 50),
        enable_rotation=CacheSettings.get("enable_rotation", True),
        enable_duplicate_detection=False  # We'll do it manually
    )

    detector = DuplicateDetector()

    print("=" * 70)
    print("  Wallpaper Duplicate Finder")
    print("=" * 70)
    print()
    print(f"Cache directory: {cache_manager.directory}")
    print()

    # Get all cache entries
    entries = cache_manager._index.get("items", [])
    total = len(entries)

    if total == 0:
        print("No wallpapers found in cache.")
        return

    print(f"Found {total} wallpapers to analyze...")
    print()

    # Step 1: Populate missing perceptual hashes
    print("Step 1: Computing perceptual hashes...")
    print("-" * 70)

    updated_count = 0
    skipped_count = 0
    error_count = 0

    for i, entry in enumerate(entries, 1):
        image_path = entry.get("path")

        # Skip if already has hash
        if "perceptual_hash" in entry and entry["perceptual_hash"]:
            skipped_count += 1
            print(f"[{i}/{total}] SKIP: {os.path.basename(image_path)} (already has hash)")
            continue

        if not os.path.exists(image_path):
            error_count += 1
            print(f"[{i}/{total}] ERROR: {os.path.basename(image_path)} (file not found)")
            continue

        try:
            print(f"[{i}/{total}] Computing hash: {os.path.basename(image_path)}...", end=" ")

            perceptual_hash = detector.compute_hash(image_path)

            if perceptual_hash:
                entry["perceptual_hash"] = perceptual_hash
                updated_count += 1
                print(f"OK - {perceptual_hash}")
            else:
                error_count += 1
                print("FAILED")

        except Exception as e:
            error_count += 1
            print(f"ERROR: {e}")

    # Save updated cache
    if updated_count > 0:
        print()
        print("Saving updated cache...")
        cache_manager._save()
        print("Done!")

    print()
    print("-" * 70)
    print(f"Hash computation summary:")
    print(f"  Total wallpapers:  {total}")
    print(f"  Updated:           {updated_count}")
    print(f"  Skipped:           {skipped_count}")
    print(f"  Errors:            {error_count}")
    print()

    # Step 2: Find duplicates
    print("Step 2: Finding duplicates...")
    print("-" * 70)

    image_paths = [entry.get("path") for entry in entries if entry.get("path") and os.path.exists(entry.get("path"))]

    if not image_paths:
        print("No valid images to compare.")
        return

    # Find duplicates with different thresholds
    thresholds = [
        (DuplicateDetector.EXACT_MATCH, "Exact duplicates"),
        (DuplicateDetector.VERY_SIMILAR, "Very similar"),
        (DuplicateDetector.SIMILAR, "Similar"),
    ]

    all_duplicates = []

    for threshold, description in thresholds:
        duplicates = detector.find_duplicates(image_paths, threshold=threshold)

        if duplicates:
            print()
            print(f"{description} (distance <= {threshold}):")
            for path1, path2, distance in duplicates:
                similarity = detector.get_similarity_description(distance)
                print(f"  - {os.path.basename(path1)}")
                print(f"    -> {os.path.basename(path2)}")
                print(f"       Distance: {distance} ({similarity})")
                all_duplicates.append((path1, path2, distance))

    print()
    print("=" * 70)
    print("  Summary")
    print("=" * 70)

    if all_duplicates:
        print(f"Found {len(all_duplicates)} duplicate/similar pairs")
        print()
        print("You can review these wallpapers in the GUI and remove unwanted duplicates.")
    else:
        print("No duplicates found! Your wallpaper collection is unique.")

    print()


if __name__ == "__main__":
    try:
        find_and_populate_duplicates()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
