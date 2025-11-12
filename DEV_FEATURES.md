# Development Branch - New Features

This branch (`dev`) contains experimental features being developed for WallpaperChanger.

## Feature 1: Color-Based Filtering ✅ COMPLETE

### What it does
Automatically extracts dominant colors from wallpapers and allows filtering by color.

### How it works
- Uses ColorThief library to analyze wallpaper images
- Categorizes colors into: blue, green, red, orange, yellow, purple, pink, dark, white, gray
- Stores color data in cache metadata (`color_categories`, `primary_color`)
- Adds "Color" filter dropdown in Wallpapers view

### Usage
1. **For new wallpapers**: Colors are extracted automatically when downloaded
2. **For existing wallpapers**: Run `python populate_colors.py` to analyze cached wallpapers

### Files
- `color_analyzer.py` - Color extraction and categorization
- `cache_manager.py` - Modified to store color data
- `gui_modern.py` - Added color filter UI
- `populate_colors.py` - Batch color analysis tool

---

## Feature 3: Dynamic Time/Weather-Based Wallpapers 🚧 IN PROGRESS

### What it does
Automatically selects wallpapers based on time of day, day of week, season, or weather conditions.

### How it works
- Rule-based system with priorities
- Rules can match on:
  - Time range (e.g., 06:00-12:00)
  - Day of week
  - Season (spring, summer, autumn, winter)
  - Weather conditions (rain, clear, etc.)
- Each rule specifies preferred tags and colors
- Multiple rules can be active at once

### Default Rules
- **Morning (6AM-12PM)**: Bright wallpapers (yellow, orange, white)
- **Evening (5PM-9PM)**: Warm wallpapers (orange, red, purple)
- **Night (9PM-6AM)**: Dark wallpapers (dark, blue, purple)
- **Rainy Days**: Rain/fog themed wallpapers (disabled by default)

### Status
- ✅ Core `DynamicRulesManager` created
- ✅ JSON-based rule storage
- ❌ Integration with main.py pending
- ❌ UI for managing rules pending

### Files
- `dynamic_rules.py` - Rule management system
- `dynamic_rules.json` - Rules configuration (auto-created)

---

## Feature 4: Duplicate Detection 🔜 TODO

Detect and remove duplicate or very similar wallpapers using perceptual hashing.

### Planned Implementation
- Use `imagehash` library (already installed)
- Calculate perceptual hash for each wallpaper
- Find duplicates with similarity threshold
- Add "Duplicates" view in GUI

---

## Feature 5: Smart Recommendations 🔜 TODO

Recommend wallpapers based on your usage patterns.

### Planned Implementation
- Analyze tags from highly-rated/frequently-used wallpapers
- Calculate similarity scores
- Suggest wallpapers with similar characteristics
- Add "Recommended for You" section in Home view

---

## Installation

These features are in the `dev` branch:

```bash
git checkout dev
pip install imagehash colorthief  # If not already installed
python populate_colors.py  # To analyze existing wallpapers
```

## Testing

To test color filtering:
1. Run `python populate_colors.py` (if you have existing wallpapers)
2. Open GUI
3. Go to "Wallpapers" tab
4. Use the "Color:" dropdown to filter

To test dynamic rules:
```bash
python dynamic_rules.py  # Shows current active rules
```

## Merging to Master

These features will be merged to `master` after:
- [ ] Feature 3 integration complete
- [ ] Feature 4 implemented
- [ ] Feature 5 implemented
- [ ] All features tested
- [ ] Documentation updated

---

**Last Updated**: 2025-11-12
**Branch**: dev
**Status**: Active Development
