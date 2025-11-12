"""
Color Analyzer Module

Extracts dominant colors from wallpapers for filtering and categorization.
"""

from colorthief import ColorThief
from PIL import Image
import os
from typing import List, Tuple, Optional


class ColorAnalyzer:
    """Analyze and extract dominant colors from images"""

    # Predefined color categories with RGB ranges
    COLOR_CATEGORIES = {
        'blue': {'hue_range': (170, 250), 'name': 'Blue'},
        'green': {'hue_range': (80, 170), 'name': 'Green'},
        'red': {'hue_range': (0, 20), 'name': 'Red'},
        'orange': {'hue_range': (20, 40), 'name': 'Orange'},
        'yellow': {'hue_range': (40, 80), 'name': 'Yellow'},
        'purple': {'hue_range': (250, 310), 'name': 'Purple'},
        'pink': {'hue_range': (310, 350), 'name': 'Pink'},
        'magenta': {'hue_range': (350, 360), 'name': 'Magenta'},
    }

    @staticmethod
    def rgb_to_hsv(r: int, g: int, b: int) -> Tuple[float, float, float]:
        """Convert RGB to HSV color space"""
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        diff = max_c - min_c

        # Hue calculation
        if diff == 0:
            h = 0
        elif max_c == r:
            h = (60 * ((g - b) / diff) + 360) % 360
        elif max_c == g:
            h = (60 * ((b - r) / diff) + 120) % 360
        else:
            h = (60 * ((r - g) / diff) + 240) % 360

        # Saturation calculation
        s = 0 if max_c == 0 else (diff / max_c)

        # Value calculation
        v = max_c

        return h, s, v

    @staticmethod
    def categorize_color(rgb: Tuple[int, int, int]) -> str:
        """Categorize RGB color into named category"""
        h, s, v = ColorAnalyzer.rgb_to_hsv(*rgb)

        # If color is too dark or desaturated, categorize as neutral
        if v < 0.2:
            return 'dark'
        if s < 0.2:
            if v > 0.8:
                return 'white'
            elif v > 0.4:
                return 'gray'
            else:
                return 'dark'

        # Find matching color category by hue
        for category, info in ColorAnalyzer.COLOR_CATEGORIES.items():
            hue_min, hue_max = info['hue_range']
            if hue_min <= h < hue_max:
                return category

        # Handle red wrapping around 360 degrees
        if h >= 350 or h < 20:
            return 'red'

        return 'other'

    @staticmethod
    def get_dominant_colors(image_path: str, num_colors: int = 5) -> List[Tuple[int, int, int]]:
        """
        Extract dominant colors from an image (FAST version using PIL)

        Args:
            image_path: Path to the image file
            num_colors: Number of dominant colors to extract

        Returns:
            List of RGB tuples representing dominant colors
        """
        if not os.path.exists(image_path):
            return []

        try:
            # Fast version: use PIL directly instead of ColorThief
            from PIL import Image

            # Open and resize image to speed up processing
            img = Image.open(image_path)
            img = img.convert('RGB')

            # Resize to max 200px for speed
            img.thumbnail((200, 200))

            # Get colors using quantize
            img = img.quantize(colors=num_colors)
            palette = img.getpalette()

            # Convert palette to list of RGB tuples
            colors = []
            for i in range(num_colors):
                r = palette[i*3]
                g = palette[i*3 + 1]
                b = palette[i*3 + 2]
                colors.append((r, g, b))

            return colors

        except Exception as e:
            print(f"[ERROR] Failed to extract colors from {image_path}: {e}")
            return []

    @staticmethod
    def get_color_categories(image_path: str, num_colors: int = 5) -> List[str]:
        """
        Get categorized color names from an image

        Args:
            image_path: Path to the image file
            num_colors: Number of colors to analyze

        Returns:
            List of color category names (e.g., ['blue', 'green', 'dark'])
        """
        dominant_colors = ColorAnalyzer.get_dominant_colors(image_path, num_colors)

        categories = []
        for rgb in dominant_colors:
            category = ColorAnalyzer.categorize_color(rgb)
            if category not in categories:
                categories.append(category)

        return categories

    @staticmethod
    def get_primary_color_category(image_path: str) -> Optional[str]:
        """
        Get the primary (most dominant) color category

        Args:
            image_path: Path to the image file

        Returns:
            Primary color category name or None if extraction fails
        """
        dominant_colors = ColorAnalyzer.get_dominant_colors(image_path, num_colors=1)

        if not dominant_colors:
            return None

        return ColorAnalyzer.categorize_color(dominant_colors[0])


# Example usage and testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        image_path = sys.argv[1]

        print(f"Analyzing: {image_path}")
        print(f"Dominant colors (RGB): {ColorAnalyzer.get_dominant_colors(image_path)}")
        print(f"Color categories: {ColorAnalyzer.get_color_categories(image_path)}")
        print(f"Primary color: {ColorAnalyzer.get_primary_color_category(image_path)}")
    else:
        print("Usage: python color_analyzer.py <image_path>")
