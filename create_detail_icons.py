#!/usr/bin/env python3
"""
Create simple PNG icons for weather details (humidity, wind, pressure, clouds)
"""
from PIL import Image, ImageDraw
import os

# Icon size (small icons for details)
SIZE = 64
ICON_DIR = "icons/weather"

# Ensure directory exists
os.makedirs(ICON_DIR, exist_ok=True)

def create_humidity_icon():
    """Create humidity icon (water droplet)"""
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw water droplet shape
    # Top point
    points = [
        (SIZE//2, SIZE//4),  # Top
        (SIZE//4, SIZE//2),  # Left curve
        (SIZE//4, SIZE*3//4 - 5),  # Left bottom
        (SIZE//2, SIZE*3//4 + 5),  # Bottom
        (SIZE*3//4, SIZE*3//4 - 5),  # Right bottom
        (SIZE*3//4, SIZE//2),  # Right curve
    ]

    # Draw droplet with gradient-like effect
    draw.polygon(points, fill=(100, 180, 255, 255), outline=(70, 150, 230, 255), width=3)

    # Add highlight
    draw.ellipse([SIZE//2 - 6, SIZE//3, SIZE//2 + 2, SIZE//3 + 8], fill=(200, 230, 255, 200))

    img.save(os.path.join(ICON_DIR, "humidity.png"))
    print("[OK] Created humidity.png")

def create_wind_icon():
    """Create wind icon (curved lines)"""
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw wind lines (curved)
    color = (150, 200, 255, 255)

    # Top line
    draw.arc([SIZE//8, SIZE//4, SIZE*7//8, SIZE//2], 0, 180, fill=color, width=5)
    draw.line([SIZE//8, SIZE*3//8, SIZE//8 - 8, SIZE*3//8], fill=color, width=5)

    # Middle line (longer)
    draw.arc([SIZE//8, SIZE*2//5, SIZE*7//8, SIZE*3//5], 0, 180, fill=color, width=5)
    draw.line([SIZE//8, SIZE//2, SIZE//8 - 8, SIZE//2], fill=color, width=5)

    # Bottom line
    draw.arc([SIZE//8, SIZE*11//20, SIZE*7//8, SIZE*3//4], 0, 180, fill=color, width=5)
    draw.line([SIZE//8, SIZE*5//8, SIZE//8 - 8, SIZE*5//8], fill=color, width=5)

    img.save(os.path.join(ICON_DIR, "wind.png"))
    print("[OK] Created wind.png")

def create_pressure_icon():
    """Create pressure icon (gauge/meter)"""
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw gauge outline
    color = (255, 200, 100, 255)
    center = (SIZE//2, SIZE//2)
    radius = SIZE//3

    # Draw semi-circle gauge
    draw.arc([center[0] - radius, center[1] - radius,
              center[0] + radius, center[1] + radius],
             180, 0, fill=color, width=5)

    # Draw tick marks
    for angle in [200, 220, 240, 260, 280, 300, 320, 340]:
        import math
        rad = math.radians(angle)
        x1 = center[0] + int(radius * 0.8 * math.cos(rad))
        y1 = center[1] + int(radius * 0.8 * math.sin(rad))
        x2 = center[0] + int(radius * math.cos(rad))
        y2 = center[1] + int(radius * math.sin(rad))
        draw.line([x1, y1, x2, y2], fill=color, width=2)

    # Draw needle
    needle_angle = 270  # Pointing up
    rad = math.radians(needle_angle)
    x_end = center[0] + int(radius * 0.7 * math.cos(rad))
    y_end = center[1] + int(radius * 0.7 * math.sin(rad))
    draw.line([center[0], center[1], x_end, y_end], fill=(255, 100, 100, 255), width=4)

    # Center dot
    draw.ellipse([center[0] - 4, center[1] - 4, center[0] + 4, center[1] + 4],
                 fill=(255, 100, 100, 255))

    img.save(os.path.join(ICON_DIR, "pressure.png"))
    print("[OK] Created pressure.png")

def create_clouds_icon():
    """Create clouds percentage icon (simplified cloud)"""
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw simple cloud shape
    color = (200, 220, 240, 255)

    # Three circles for cloud
    y_base = SIZE//2 + 5
    draw.ellipse([SIZE//4 - 8, y_base - 15, SIZE//4 + 12, y_base + 5], fill=color)
    draw.ellipse([SIZE//2 - 10, y_base - 20, SIZE//2 + 10, y_base], fill=color)
    draw.ellipse([SIZE*3//4 - 12, y_base - 15, SIZE*3//4 + 8, y_base + 5], fill=color)

    # Base rectangle to connect
    draw.rectangle([SIZE//4 - 8, y_base - 10, SIZE*3//4 + 8, y_base + 5], fill=color)

    img.save(os.path.join(ICON_DIR, "clouds_detail.png"))
    print("[OK] Created clouds_detail.png")

if __name__ == "__main__":
    print("Creating weather detail icons...")
    create_humidity_icon()
    create_wind_icon()
    create_pressure_icon()
    create_clouds_icon()
    print("\nAll icons created successfully!")
    print(f"Icons saved in: {os.path.abspath(ICON_DIR)}")
