# Quick Fixes to Re-apply

## File: smart_recommendations.py

### 1. Optimized Prompt (Line ~509-544)
Replace the huge prompt with:
```python
# Build FAST and concise prompt (optimized for speed)
top_tags = ', '.join([tag for tag, _ in preferences['top_tags'][:3]])

# Time-based rules (super concise)
if 6 <= hour <= 11:
    time_hint = "Morning: use bright/light/clean"
elif 12 <= hour <= 17:
    time_hint = "Afternoon: use vibrant/colorful/warm"
elif 18 <= hour <= 22:
    time_hint = "Evening: use warm/cozy/sunset"
else:
    time_hint = "Night: use dark/blue/peaceful"

prompt = f"""Detect mood and suggest 3 wallpaper searches (2-3 words each).

Time: {hour}:00 ({day_of_week})
User likes: {top_tags or 'minimal, nature, abstract'}
Energy: {time_mood_score['energy']:.0f}/10
Focus: {time_mood_score['focus']:.0f}/10

{time_hint}

Rules:
- 2-3 words per query
- Match time with colors
- No technical terms

Format:
MOOD: [energetic/calm/focused/creative/relaxed/inspired]
SECONDARY: [mood or none]
CONFIDENCE: [0-100]%
REASONING: [max 8 words]
STYLE: [3-5 words]
QUERY1: [2-3 words]
QUERY2: [2-3 words]
QUERY3: [2-3 words]"""

response_text = self._generate_content(prompt)
result = response_text.strip()
```

## File: gui_modern.py

### CRITICAL FIXES LOST:
1. AILoadingDialog class (lines 31-83)
2. Privacy mode checkbox (lines 3500-3570)
3. Threading in _detect_mood_ai (lines 4086-4127)
4. _toggle_local_ai_mode function (lines 4041-4084)
5. Safe dialog closing (lines 4129-4137)

### Current Status:
- ❌ No loading dialog
- ❌ No privacy checkbox
- ❌ UI freezes
- ✅ Image validation (just added)

## RECOMMENDATION:
Don't use `git checkout` - it destroys all work!
Use `git stash` or create backup file first.
