"""Test script to verify cache and image loading"""
import os
from PIL import Image
from cache_manager import CacheManager
from config import CacheSettings

def test_cache():
    print("=" * 60)
    print("Testing Cache Manager")
    print("=" * 60)

    cache_dir = CacheSettings.get("directory") or os.path.join(
        os.path.expanduser("~"), "WallpaperChangerCache"
    )

    print(f"\nCache directory: {cache_dir}")
    print(f"Directory exists: {os.path.exists(cache_dir)}")

    cache_manager = CacheManager(
        cache_dir,
        max_items=int(CacheSettings.get("max_items", 60)),
        enable_rotation=bool(CacheSettings.get("enable_offline_rotation", True)),
    )

    entries = cache_manager.list_entries()
    print(f"\nTotal cached entries: {len(entries)}")

    if entries:
        print("\nFirst 5 entries:")
        for idx, entry in enumerate(entries[:5]):
            path = entry.get("path", "NO PATH")
            exists = os.path.exists(path) if path else False
            print(f"\n  Entry {idx + 1}:")
            print(f"    Path: {path}")
            print(f"    Exists: {exists}")
            print(f"    Source: {entry.get('source_info', 'Unknown')[:50]}")

            if exists:
                try:
                    img = Image.open(path)
                    print(f"    Image size: {img.size}")
                    print(f"    Image mode: {img.mode}")
                    img.close()
                    print(f"    ✓ Image loads successfully")
                except Exception as e:
                    print(f"    ✗ Error loading image: {e}")
    else:
        print("\n⚠ No entries found in cache!")
        print("\nChecking cache directory contents:")
        if os.path.exists(cache_dir):
            files = os.listdir(cache_dir)
            image_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
            print(f"  Total files: {len(files)}")
            print(f"  Image files: {len(image_files)}")
            if image_files:
                print(f"  Sample files: {image_files[:5]}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_cache()
