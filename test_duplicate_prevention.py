"""
Test Duplicate Prevention During Download

Tests that the cache manager correctly prevents downloading duplicate wallpapers
across different monitors.
"""

import os
import sys
import shutil
import tempfile
from PIL import Image

# Force UTF-8 encoding for console output
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cache_manager import CacheManager
from duplicate_detector import DuplicateDetector


def create_test_image(path, color=(255, 0, 0), size=(1920, 1080), pattern="gradient"):
    """Create a test image with specified color and pattern"""
    from PIL import ImageDraw
    img = Image.new('RGB', size, color)

    if pattern == "gradient":
        # Create gradient to make images distinguishable
        draw = ImageDraw.Draw(img)
        for y in range(size[1]):
            gradient_color = (
                int(color[0] * (1 - y/size[1])),
                int(color[1] * (1 - y/size[1])),
                int(color[2] * (1 - y/size[1]))
            )
            draw.line([(0, y), (size[0], y)], fill=gradient_color)
    elif pattern == "circles":
        # Draw circles pattern
        draw = ImageDraw.Draw(img)
        for i in range(10):
            x = (i * size[0]) // 10
            draw.ellipse([x, size[1]//4, x+200, size[1]//4+200], fill=(255, 255, 255))

    img.save(path)
    return path


def test_duplicate_prevention():
    """Test that duplicates are prevented across monitors"""
    print("=" * 70)
    print("  Duplicate Prevention Test")
    print("=" * 70)
    print()

    # Create temporary cache directory
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = os.path.join(temp_dir, "cache")
        os.makedirs(cache_dir, exist_ok=True)

        # Initialize cache manager with duplicate detection enabled
        cache = CacheManager(
            directory=cache_dir,
            max_items=10,
            enable_rotation=False,
            enable_duplicate_detection=True
        )

        print(f"Cache directory: {cache_dir}")
        print()

        # Create test images directory
        test_images_dir = os.path.join(temp_dir, "test_images")
        os.makedirs(test_images_dir, exist_ok=True)

        # Test 1: Store first wallpaper for monitor 0
        print("Test 1: Store original wallpaper for monitor 0")
        print("-" * 70)
        img1_path = os.path.join(test_images_dir, "red_wallpaper.jpg")
        create_test_image(img1_path, color=(255, 0, 0))

        result1 = cache.store(img1_path, {
            "source_info": "Test Red Wallpaper",
            "unique_id": "test_red_1",
            "monitor_index": 0
        })

        if result1:
            print(f"✓ Stored: {os.path.basename(result1)}")
        else:
            print("✗ Failed to store")
            return False

        print()

        # Test 2: Try to store SAME wallpaper for monitor 1 (should be blocked)
        print("Test 2: Try to store identical wallpaper for monitor 1")
        print("-" * 70)
        img2_path = os.path.join(test_images_dir, "red_wallpaper_copy.jpg")
        shutil.copy2(img1_path, img2_path)  # Exact copy

        result2 = cache.store(img2_path, {
            "source_info": "Test Red Wallpaper Copy",
            "unique_id": "test_red_2",  # Different ID
            "monitor_index": 1  # Different monitor
        })

        if result2 == result1:
            print(f"✓ DUPLICATE DETECTED! Reused: {os.path.basename(result2)}")
            print(f"  Cross-monitor duplicate prevention working correctly!")
        else:
            print(f"✗ DUPLICATE NOT DETECTED! Stored as new: {os.path.basename(result2)}")
            print(f"  Expected to reuse {os.path.basename(result1)}")
            return False

        print()

        # Test 3: Store a different wallpaper (should succeed)
        print("Test 3: Store different wallpaper for monitor 1")
        print("-" * 70)
        img3_path = os.path.join(test_images_dir, "blue_wallpaper.jpg")
        create_test_image(img3_path, color=(0, 0, 255), pattern="circles")

        result3 = cache.store(img3_path, {
            "source_info": "Test Blue Wallpaper",
            "unique_id": "test_blue_1",
            "monitor_index": 1
        })

        if result3 and result3 != result1:
            print(f"✓ Stored new wallpaper: {os.path.basename(result3)}")
        else:
            print("✗ Failed to store different wallpaper")
            return False

        print()

        # Test 4: Try slightly modified version (should still be blocked if similar enough)
        print("Test 4: Try slightly modified version of red wallpaper")
        print("-" * 70)
        img4_path = os.path.join(test_images_dir, "red_wallpaper_modified.jpg")
        # Create very similar image (slightly different red)
        create_test_image(img4_path, color=(250, 5, 5))

        result4 = cache.store(img4_path, {
            "source_info": "Test Red Wallpaper Modified",
            "unique_id": "test_red_3",
            "monitor_index": 0
        })

        if result4 == result1:
            print(f"✓ SIMILAR IMAGE DETECTED! Reused: {os.path.basename(result4)}")
            print(f"  Perceptual hashing working correctly!")
        else:
            print(f"⚠ Similar image stored as new (threshold may need adjustment)")
            print(f"  Stored: {os.path.basename(result4)}")

        print()
        print("=" * 70)
        print("  Summary")
        print("=" * 70)

        # Check cache index
        cache_items = cache._index.get("items", [])
        print(f"Total unique wallpapers in cache: {len(cache_items)}")
        print()

        if len(cache_items) <= 2:
            print("✓ DUPLICATE PREVENTION WORKING!")
            print("  Cross-monitor duplicates were successfully prevented.")
            return True
        else:
            print("✗ DUPLICATE PREVENTION FAILED!")
            print(f"  Expected max 2 unique wallpapers, found {len(cache_items)}")
            return False


if __name__ == "__main__":
    try:
        success = test_duplicate_prevention()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
