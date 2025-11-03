# Weather Rotation Fixes - Summary

## Issues Fixed

### 1. Provider Rotation Not Working ✅
**Problem**: System was ignoring `RotateProviders = True` and `ProvidersSequence`, always using hardcoded providers from playlist entries.

**Root Cause**: Playlist entries had hardcoded `'provider': 'wallhaven'` or `'provider': 'pexels'` which overrode global rotation settings.

**Fix**: Removed all hardcoded provider fields from playlist entries in [config.py](config.py) using regex.

**Verification**:
```bash
# Check logs should show rotation
tail -f wallpaperchanger.log
# Should see: "using providers reddit/wallhaven/pexels" rotating
```

---

### 2. Triple Wallpaper Change on Hotkey ✅
**Problem**: Each Ctrl+Alt+W press changed wallpaper 3 times instead of once.

**Root Cause**: The `keyboard.add_hotkey()` was triggering multiple times (likely key down/up events).

**Fix**: Added debounce mechanism in [main.py](main.py):
- Added `self._last_change_time` and `self._change_lock` to `__init__` (lines 356-358)
- Implemented 1-second debounce in `change_wallpaper()` method (lines 728-739)
- Only applies to user-triggered events (hotkey, GUI, tray)
- Automated triggers (startup, scheduler) bypass debounce

**Code Added**:
```python
# In __init__:
self._last_change_time = 0.0
self._change_lock = threading.Lock()

# In change_wallpaper():
if trigger in ["hotkey", "gui", "tray"]:
    with self._change_lock:
        if current_time - self._last_change_time < 1.0:
            self.logger.debug(f"Ignoring duplicate {trigger} trigger (debounce)")
            return
        self._last_change_time = current_time
```

---

### 3. GUI Corrupting config.py on Save ✅
**Problem**: When saving configuration, `Playlists` and `WeatherRotationSettings` sections were being deleted.

**Root Cause**: In [gui_config.py](gui_config.py) `_save_config()` method, the skip logic used `continue` without first appending the line:
```python
if skip_playlists:
    if stripped.startswith("]"):
        skip_playlists = False
    continue  # ← BUG: Skips appending line, loses data!
```

**Fix**: Changed to preserve lines before continue (line 2732):
```python
if skip_playlists:
    new_lines.append(line)  # ← FIXED: Preserve the line!
    if stripped.startswith("]"):
        skip_playlists = False
    continue
```

---

### 4. GUI Not Saving Weather Settings Changes ✅
**Problem**: After fixing corruption, GUI would show "Configuration saved successfully" but user edits to weather settings weren't being saved to [config.py](config.py).

**Root Cause**: The "preserve original lines" fix meant ALL lines in the WeatherRotationSettings block were copied verbatim, ignoring user input from GUI fields.

**Challenge**: WeatherRotationSettings has a nested `"location": {...}` dictionary structure that needed special handling.

**Fix**: Implemented selective field updating in [gui_config.py](gui_config.py) (lines 2736-2799):

1. Added `in_weather_location` flag to track when inside nested location dict (line 2721)
2. Detect location dict start: `if '"location":' in line and '{' in line` (line 2738)
3. Update only GUI-modifiable fields:
   - `enabled`, `refresh_minutes`, `units`, `apply_on` (root level)
   - `city`, `country`, `latitude`, `longitude` (inside location dict)
4. Preserve other fields as-is: `api_key`, `provider`, `conditions`
5. Track exiting location dict with `if stripped.startswith("},")` (line 2793)

**Code Logic**:
```python
if skip_weather:
    # Detect location dict opening
    if '"location":' in line and '{' in line:
        in_weather_location = True
        new_lines.append(line)

    # Update GUI-editable fields at root level
    elif '"enabled":' in line:
        indent = line[:len(line) - len(line.lstrip())]
        enabled_val = self.weather_enabled_var.get()
        new_lines.append(f'{indent}"enabled": {enabled_val},\n')

    # Update location fields only when inside location dict
    elif in_weather_location and '"city":' in line:
        indent = line[:len(line) - len(line.lstrip())]
        city_val = self.weather_city_var.get()
        new_lines.append(f'{indent}"city": "{city_val}",\n')

    # Preserve other lines (api_key, provider, conditions)
    else:
        new_lines.append(line)

    # Detect location dict closing
    if in_weather_location and stripped.startswith("},"):
        in_weather_location = False

    # Detect weather settings block closing
    if stripped.startswith("}") and not in_weather_location:
        skip_weather = False
```

---

## Expected config.py Structure

```python
WeatherRotationSettings = {
    "enabled": True,
    "provider": "openweathermap",
    "api_key": os.getenv("OPENWEATHER_API_KEY", ""),
    "refresh_minutes": 30,
    "apply_on": ["startup", "scheduler", "hotkey"],
    "units": "metric",
    "location": {
        "city": "Milan",
        "country": "IT",
        "latitude": 45.4642,
        "longitude": 9.19,
    },
    "conditions": {
        "clear": {"playlist": "sunny_work"},
        "night_clear": {"playlist": "night_calm"},
        # ... more conditions
    },
}
```

**Key Points**:
- ✅ `location` is a NESTED dictionary (not flattened)
- ✅ Location fields (`city`, `country`, `latitude`, `longitude`) are inside `location` dict
- ✅ Other fields (`enabled`, `provider`, `api_key`, etc.) are at root level

---

## Testing

### Test Scripts Created

1. **test_gui_weather_save.py** - Verifies config.py structure
   - Checks for nested `"location": {...}` dict
   - Extracts and displays current values
   - Detects if structure is flattened (incorrect)

2. **test_gui_save_logic.py** - Simulates GUI save operation
   - Simulates user editing weather settings
   - Runs save logic without actually opening GUI
   - Verifies output preserves nested structure
   - Confirms all values updated correctly

### How to Test

```bash
# 1. Check current structure
python test_gui_weather_save.py

# 2. Test save logic simulation
python test_gui_save_logic.py

# 3. Test with actual GUI
python gui_config.py
# - Navigate to Advanced tab → Weather-Based Rotation
# - Modify city to "Cameri"
# - Modify refresh to 45 minutes
# - Click "Save Configuration"
# - Close and reopen GUI
# - Verify values are still "Cameri" and 45

# 4. Verify config.py structure after save
python test_gui_weather_save.py
# Should show nested location dict preserved
```

---

## Verification Checklist

After applying fixes:

- [ ] Provider rotation works (logs show reddit → wallhaven → pexels)
- [ ] Single hotkey press = single wallpaper change
- [ ] GUI saves without losing Playlists section
- [ ] GUI saves without losing WeatherRotationSettings section
- [ ] Weather settings changes in GUI persist after save
- [ ] Location dict remains nested (not flattened)
- [ ] API key field preserved when saving other weather settings
- [ ] Conditions mappings preserved when saving other weather settings

---

## Files Modified

1. **[config.py](config.py)**
   - Removed hardcoded provider fields from playlists
   - Restored proper nested location structure

2. **[main.py](main.py)**
   - Added debounce mechanism for wallpaper changes (lines 356-358, 728-739)

3. **[gui_config.py](gui_config.py)**
   - Fixed playlist preservation (line 2732)
   - Implemented selective weather settings update (lines 2721, 2736-2799)
   - Added nested location dict tracking

---

## Helper Scripts

- `update_config_final.py` - Applies all weather improvements
- `enable_weather_quick.py` - Quick enable weather rotation
- `fix_playlist_providers.py` - Remove provider overrides
- `test_weather_rotation.py` - Test weather conditions mapping
- `test_gui_weather_save.py` - Verify config structure ✨ NEW
- `test_gui_save_logic.py` - Simulate GUI save ✨ NEW

---

## Next Steps

1. **Test GUI save/load workflow**
   ```bash
   python gui_config.py
   # Make changes → Save → Close → Reopen → Verify
   ```

2. **Test weather rotation**
   ```bash
   python test_weather_rotation.py
   # Should show current weather and which playlist/preset would be used
   ```

3. **Monitor logs**
   ```bash
   tail -f wallpaperchanger.log
   # Watch for weather decisions and provider rotation
   ```

4. **Restart service**
   ```bash
   python launchers/stop_wallpaper_changer.py
   python main.py
   # Weather should apply on startup if in apply_on list
   ```

---

## Known Limitations

- Weather API key can take up to 2 hours to activate after creation
- OpenWeatherMap free tier: 1000 calls/day (more than sufficient)
- Refresh minimum: 30 minutes recommended to stay within quota
- Provider rotation changes on each wallpaper update (not time-based)

---

## Troubleshooting

**Weather not applying?**
1. Check `"enabled": True` in WeatherRotationSettings
2. Verify API key is set: `os.getenv("OPENWEATHER_API_KEY")`
3. Check if trigger is in `apply_on` list
4. Run `python test_weather_rotation.py` to test API

**Provider still not rotating?**
1. Verify `RotateProviders = True`
2. Check logs for "using providers reddit/wallhaven/pexels"
3. Ensure NO playlist entries have `'provider'` field
4. Run `git diff config.py` to see if providers were removed

**GUI not saving changes?**
1. Check config.py has nested `"location": {...}` structure
2. Run `python test_gui_weather_save.py` before and after save
3. Check GUI console for errors
4. Verify file permissions on config.py

**Triple wallpaper change still happening?**
1. Check main.py has debounce code (lines 356-358, 728-739)
2. Restart the service to load new code
3. Check logs for "Ignoring duplicate hotkey trigger (debounce)"
