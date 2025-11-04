#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weather Overlay Module
Draws weather information on wallpaper images
"""

import os
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from dataclasses import dataclass


@dataclass
class WeatherInfo:
    """Weather information for overlay"""
    city: str
    country: str
    condition: str
    temperature: float
    humidity: Optional[int] = None
    wind_speed: Optional[float] = None
    icon: Optional[str] = None
    feels_like: Optional[float] = None
    pressure: Optional[int] = None
    clouds: Optional[int] = None
    description: Optional[str] = None


class WeatherOverlay:
    """Draws weather information overlay on wallpaper images"""

    # Weather emoji mapping (will be converted to symbols)
    WEATHER_SYMBOLS = {
        "clear": "☀",
        "night_clear": "☾",
        "clouds": "☁",
        "rain": "☂",
        "drizzle": "☂",
        "snow": "❄",
        "thunderstorm": "⚡",
        "mist": "≡",
        "fog": "≡",
        "storm": "⚡",
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize weather overlay

        Args:
            config: Optional configuration dict with:
                - enabled: bool (default True)
                - position: str ("top-left", "top-right", "bottom-left", "bottom-right")
                - opacity: float (0.0-1.0, default 0.85)
                - font_size: int (default 36)
                - padding: int (default 30)
                - background_blur: int (default 20)
                - background_color: tuple (R, G, B, A)
                - text_color: tuple (R, G, B)
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.position = self.config.get("position", "top-right")
        self.opacity = self.config.get("opacity", 0.85)
        self.font_size = self.config.get("font_size", 36)
        self.padding = self.config.get("padding", 30)
        self.background_blur = self.config.get("background_blur", 20)
        self.background_color = self.config.get("background_color", (30, 30, 46, 230))
        self.text_color = self.config.get("text_color", (205, 214, 244))

        # Load font
        self.font = self._load_font()
        self.font_small = self._load_font(int(self.font_size * 0.6))

        # Icon settings
        self.icon_size = int(self.font_size * 1.5)  # Icon size relative to font
        self.icons_dir = Path(__file__).parent / "icons" / "weather"

    def _load_font(self, size: Optional[int] = None) -> ImageFont.FreeTypeFont:
        """Load font with fallback to default"""
        size = size or self.font_size

        # Try to load nice fonts on Windows
        font_paths = [
            "C:/Windows/Fonts/segoeui.ttf",  # Segoe UI
            "C:/Windows/Fonts/arial.ttf",    # Arial
            "C:/Windows/Fonts/calibri.ttf",  # Calibri
        ]

        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception:
                    continue

        # Fallback to default font
        return ImageFont.load_default()

    def _load_weather_icon(self, condition: str) -> Optional[Image.Image]:
        """Load weather icon PNG, return None if not found"""
        icon_path = self.icons_dir / f"{condition}.png"

        if not icon_path.exists():
            return None

        try:
            icon = Image.open(icon_path).convert("RGBA")
            # Resize to desired size maintaining aspect ratio
            icon.thumbnail((self.icon_size, self.icon_size), Image.Resampling.LANCZOS)
            return icon
        except Exception as e:
            print(f"Failed to load icon {icon_path}: {e}")
            return None

    def _load_detail_icon(self, icon_name: str, size: int) -> Optional[Image.Image]:
        """Load small detail icon (humidity, wind, pressure, clouds_detail)"""
        icon_path = self.icons_dir / f"{icon_name}.png"

        if not icon_path.exists():
            return None

        try:
            icon = Image.open(icon_path).convert("RGBA")
            # Resize to desired size maintaining aspect ratio
            icon.thumbnail((size, size), Image.Resampling.LANCZOS)
            return icon
        except Exception as e:
            return None

    def apply_overlay(
        self,
        image_path: str,
        output_path: str,
        weather_info: WeatherInfo,
        target_size: Optional[Tuple[int, int]] = None
    ) -> bool:
        """
        Apply weather overlay to image

        Args:
            image_path: Path to source image
            output_path: Path to save overlayed image
            weather_info: Weather information to display
            target_size: Optional target screen size for consistent positioning

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Open image
            img = Image.open(image_path)

            # Resize image to target size first if specified
            # This ensures the overlay is positioned correctly on the final image
            if target_size and target_size != img.size:
                from PIL import ImageOps
                try:
                    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
                except AttributeError:
                    RESAMPLE_LANCZOS = Image.LANCZOS
                img = ImageOps.fit(img, target_size, method=RESAMPLE_LANCZOS)

            # Convert to RGBA for blur effect
            if img.mode != 'RGBA':
                img = img.convert('RGBA')

            # Create overlay using the actual image size (after resize)
            # Position will now be correct since image matches target size
            # Pass source image for blur effect
            overlay = self._create_overlay(img.size, weather_info, img.size, source_image=img)

            # Composite overlay onto image
            if overlay.mode != 'RGBA':
                overlay = overlay.convert('RGBA')

            # Blend images (img is already RGBA from above)
            result = Image.alpha_composite(img, overlay)

            # Convert back to RGB for saving as JPEG
            if output_path.lower().endswith(('.jpg', '.jpeg')):
                result = result.convert('RGB')

            # Save result
            result.save(output_path, quality=95)
            return True

        except Exception as e:
            print(f"Error applying weather overlay: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _create_overlay(
        self,
        image_size: Tuple[int, int],
        weather_info: WeatherInfo,
        target_size: Optional[Tuple[int, int]] = None,
        source_image: Optional[Image.Image] = None
    ) -> Image.Image:
        """Create transparent overlay with weather info

        Args:
            image_size: Actual image dimensions
            weather_info: Weather data to display
            target_size: Target screen size for positioning (if different from image)
            source_image: Optional source image for blur effect
        """
        width, height = image_size
        # Use target size for position calculation if provided
        pos_width, pos_height = target_size if target_size else image_size

        # Create transparent overlay
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Try to load weather icon PNG, fallback to symbol
        weather_icon = self._load_weather_icon(weather_info.icon or "clear")
        use_icon = weather_icon is not None

        # Format text lines
        temp_str = f"{weather_info.temperature:.0f}°C"
        location_str = f"{weather_info.city}, {weather_info.country}"
        condition_str = self._translate_condition(weather_info.condition)

        # Add feels like if available and different from actual temp
        if weather_info.feels_like is not None:
            feels_diff = abs(weather_info.feels_like - weather_info.temperature)
            if feels_diff >= 2:  # Only show if difference is significant
                temp_str = f"{temp_str} (percepita {weather_info.feels_like:.0f}°C)"

        # Build info lines (without icon in text if we have PNG icon)
        if use_icon:
            lines = [
                location_str,  # No symbol, we'll draw PNG icon separately
                f"{temp_str}",
            ]
            # Add description if available
            if weather_info.description:
                lines.append(weather_info.description.capitalize())
        else:
            # Fallback to symbol if no PNG icon available
            symbol = self.WEATHER_SYMBOLS.get(weather_info.icon or "clear", "☀")
            lines = [
                f"{symbol}  {location_str}",
                f"{temp_str} {condition_str}",
            ]

        # Prepare detail items with icons
        detail_items = []
        if weather_info.humidity is not None:
            detail_items.append(("humidity", f"{weather_info.humidity}%"))
        if weather_info.wind_speed is not None:
            # Convert m/s to km/h if needed
            wind_kmh = weather_info.wind_speed * 3.6 if weather_info.wind_speed < 50 else weather_info.wind_speed
            detail_items.append(("wind", f"{wind_kmh:.0f} km/h"))
        if weather_info.pressure is not None:
            detail_items.append(("pressure", f"{weather_info.pressure} hPa"))
        if weather_info.clouds is not None:
            detail_items.append(("clouds_detail", f"{weather_info.clouds}%"))

        # Load detail icons (small icons for weather details)
        detail_icon_size = int(self.font_small.size * 0.8)  # Slightly smaller than text
        detail_icons = []
        for icon_name, _ in detail_items:
            icon = self._load_detail_icon(icon_name, detail_icon_size)
            detail_icons.append(icon)

        # Calculate text dimensions
        line_heights = []
        max_width = 0

        for i, line in enumerate(lines):
            font = self.font if i < 2 else self.font_small
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            line_height = bbox[3] - bbox[1]
            line_heights.append(line_height)
            max_width = max(max_width, line_width)

        # Calculate width of detail row (icons + text)
        detail_row_width = 0
        detail_row_height = 0
        if detail_items:
            # Calculate total width: icon + text + spacing for each item
            spacing_between = 15  # Space between each detail item
            for i, (icon_name, text) in enumerate(detail_items):
                bbox = draw.textbbox((0, 0), text, font=self.font_small)
                text_width = bbox[2] - bbox[0]
                # icon width + small gap + text width
                item_width = detail_icon_size + 5 + text_width
                detail_row_width += item_width
                if i < len(detail_items) - 1:
                    detail_row_width += spacing_between

            detail_row_height = max(detail_icon_size, self.font_small.size) + 10
            line_heights.append(detail_row_height)
            max_width = max(max_width, detail_row_width)

        # Calculate box dimensions (add space for icon if using PNG)
        icon_space = self.icon_size + 15 if use_icon else 0  # Icon + margin
        box_width = max_width + self.padding * 2 + icon_space

        # Calculate vertical spacing between lines
        num_text_lines = len(lines)
        total_line_spacing = 0
        for i in range(num_text_lines - 1):
            total_line_spacing += 12 if i < 2 else 8
        # Add spacing before detail row
        if detail_items:
            total_line_spacing += 8

        box_height = max(
            sum(line_heights) + self.padding * 2 + total_line_spacing,
            self.icon_size + self.padding * 2 if use_icon else 0
        )

        # Calculate position using target dimensions for consistency
        x, y = self._calculate_position(pos_width, pos_height, box_width, box_height)

        # Apply background blur effect if enabled and source image provided
        if self.background_blur > 0 and source_image:
            # Extract the region where the overlay will be placed
            box_region = (
                max(0, x),
                max(0, y),
                min(width, x + box_width),
                min(height, y + box_height)
            )

            # Crop and blur the background region
            try:
                bg_region = source_image.crop(box_region)
                blurred_bg = bg_region.filter(ImageFilter.GaussianBlur(radius=self.background_blur))

                # Paste the blurred region back
                overlay.paste(blurred_bg, (box_region[0], box_region[1]))
            except Exception as e:
                print(f"Failed to apply blur effect: {e}")

        # Draw semi-transparent background with rounded corners
        self._draw_rounded_rectangle(
            draw,
            (x, y, x + box_width, y + box_height),
            radius=20,
            fill=self.background_color
        )

        # Draw weather icon PNG if available
        text_x_offset = x + self.padding
        if use_icon and weather_icon:
            icon_y = y + (box_height - self.icon_size) // 2  # Center vertically
            overlay.paste(weather_icon, (x + self.padding, icon_y), weather_icon)
            text_x_offset += self.icon_size + 15  # Shift text to make room for icon

        # Draw text lines
        text_y = y + self.padding
        for i, line in enumerate(lines):
            font = self.font if i < 2 else self.font_small
            draw.text(
                (text_x_offset, text_y),
                line,
                fill=self.text_color,
                font=font
            )
            # Add more vertical spacing between lines (larger for bigger fonts)
            line_spacing = 12 if i < 2 else 8
            text_y += line_heights[i] + line_spacing

        # Draw detail items with icons
        if detail_items:
            detail_x = text_x_offset
            detail_y = text_y + 8  # Add small vertical spacing from previous line
            spacing_between = 20  # Increased spacing between items

            for i, ((icon_name, text), icon) in enumerate(zip(detail_items, detail_icons)):
                # Draw icon if available
                if icon:
                    # Get actual icon size after loading
                    icon_width = icon.width if icon else detail_icon_size
                    icon_y_centered = detail_y + (detail_row_height - detail_icon_size) // 2
                    overlay.paste(icon, (detail_x, icon_y_centered), icon)
                    detail_x += icon_width + 8  # Increased gap between icon and text
                else:
                    # If no icon, just add the space
                    detail_x += detail_icon_size + 8

                # Draw text - calculate position more carefully
                text_y_centered = detail_y + (detail_row_height - self.font_small.size) // 2

                # Get exact text bounding box for precise positioning
                bbox = draw.textbbox((detail_x, text_y_centered), text, font=self.font_small)
                text_width = bbox[2] - bbox[0]

                draw.text(
                    (detail_x, text_y_centered),
                    text,
                    fill=self.text_color,
                    font=self.font_small
                )

                # Move to next item position
                detail_x += text_width + spacing_between

        return overlay

    def _draw_rounded_rectangle(
        self,
        draw: ImageDraw.ImageDraw,
        xy: Tuple[int, int, int, int],
        radius: int,
        fill: Tuple[int, int, int, int]
    ) -> None:
        """Draw rounded rectangle"""
        x1, y1, x2, y2 = xy

        # Draw main rectangle
        draw.rectangle((x1 + radius, y1, x2 - radius, y2), fill=fill)
        draw.rectangle((x1, y1 + radius, x2, y2 - radius), fill=fill)

        # Draw corners
        draw.pieslice((x1, y1, x1 + radius * 2, y1 + radius * 2), 180, 270, fill=fill)
        draw.pieslice((x2 - radius * 2, y1, x2, y1 + radius * 2), 270, 360, fill=fill)
        draw.pieslice((x1, y2 - radius * 2, x1 + radius * 2, y2), 90, 180, fill=fill)
        draw.pieslice((x2 - radius * 2, y2 - radius * 2, x2, y2), 0, 90, fill=fill)

    def _calculate_position(
        self,
        img_width: int,
        img_height: int,
        box_width: int,
        box_height: int
    ) -> Tuple[int, int]:
        """Calculate overlay position based on config"""
        margin = 40

        positions = {
            "top-left": (margin, margin),
            "top-right": (img_width - box_width - margin, margin),
            "bottom-left": (margin, img_height - box_height - margin),
            "bottom-right": (img_width - box_width - margin, img_height - box_height - margin),
        }

        return positions.get(self.position, positions["top-right"])

    def _translate_condition(self, condition: str) -> str:
        """Translate weather condition to Italian"""
        translations = {
            "clear": "Sereno",
            "night_clear": "Sereno",
            "clouds": "Nuvoloso",
            "rain": "Pioggia",
            "drizzle": "Pioggerella",
            "snow": "Neve",
            "thunderstorm": "Temporale",
            "mist": "Foschia",
            "fog": "Nebbia",
            "storm": "Tempesta",
        }

        return translations.get(condition.lower(), condition.capitalize())


# Quick test function
def test_overlay():
    """Test weather overlay"""
    print("Testing weather overlay...")

    # Create test weather info
    weather = WeatherInfo(
        city="Milano",
        country="IT",
        condition="clear",
        temperature=18.4,
        humidity=65,
        wind_speed=12.5,
        icon="clear"
    )

    # Create overlay
    overlay = WeatherOverlay({
        "enabled": True,
        "position": "top-right",
        "opacity": 0.85,
    })

    # Test with a sample image (if exists)
    cache_dir = Path.home() / "WallpaperChangerCache"
    if cache_dir.exists():
        images = list(cache_dir.glob("*.jpg"))
        if images:
            test_img = images[0]
            output = cache_dir / "test_overlay.jpg"

            print(f"Applying overlay to: {test_img}")
            success = overlay.apply_overlay(str(test_img), str(output), weather)

            if success:
                print(f"✅ Overlay created: {output}")
            else:
                print("❌ Failed to create overlay")
        else:
            print("No test images found in cache")
    else:
        print("Cache directory not found")


if __name__ == "__main__":
    test_overlay()
