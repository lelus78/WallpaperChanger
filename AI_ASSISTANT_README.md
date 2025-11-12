# AI Assistant - Smart Recommendations

## Overview

The AI Assistant tab provides AI-powered wallpaper recommendations and suggestions using Google Gemini AI.

## Features

### 1. Smart Recommendations
- **Personalized suggestions** based on your usage patterns
- **Multi-factor scoring system**:
  - Favorite tags (40% weight)
  - Preferred colors (20% weight)
  - Favorite providers (15% weight)
  - Rating similarity (15% weight)
  - Novelty/freshness (10% weight)
- **Visual scores** showing why each wallpaper is recommended
- **Real-time updates** as you use the app more

### 2. AI-Generated Search Suggestions
- **Requires Google Gemini API key**
- Analyzes your preferences to suggest new search queries
- Helps you discover wallpapers matching your taste
- Based on your favorite tags, colors, and viewing patterns

## Setup

### Getting a Google Gemini API Key (Free)

1. Visit https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated API key

### Adding Your API Key

1. Open the Wallpaper Changer GUI
2. Click on "AI Assistant" in the sidebar
3. Paste your API key in the text field
4. Click "Save API Key"
5. You'll see "✓ API Key Configured" if successful

## How It Works

### Basic Recommendations (No API Required)
Even without an API key, you get basic recommendations based on:
- Tags you view most often
- Colors you prefer
- Providers you use most
- Your rating patterns
- Wallpapers you haven't seen yet

### AI-Enhanced Suggestions (Requires API)
With a Gemini API key, you also get:
- Intelligent search query suggestions
- Context-aware recommendations
- Discovery of new themes based on your style

## Privacy

- Your API key is stored locally in the app configuration
- No usage data is sent to external servers except Gemini API calls
- All recommendations are calculated locally using your statistics
- Gemini API is only used for generating search suggestions

## Tips

- **Use the app regularly** - The more you use it, the better the recommendations
- **Rate wallpapers** - Ratings help improve suggestions
- **Mark favorites** - Favorites have higher weight in recommendations
- **Try suggested queries** - AI suggestions help discover new wallpapers

## Troubleshooting

### "Invalid API Key" Error
- Double-check you copied the entire key
- Make sure the key is from https://makersuite.google.com/app/apikey
- Verify the key hasn't been revoked or expired

### "Not enough data yet" Message
- Keep using the app to build up statistics
- View, rate, and favorite wallpapers
- Recommendations improve over time

### No Recommendations Showing
- Make sure you have wallpapers in your cache
- Check that wallpapers haven't been banned
- Try refreshing recommendations with the "↻ Refresh" button

## Future AI Features

The AI Assistant tab will be expanded with more features:
- Dynamic Rules integration
- Automatic playlist creation
- Mood-based recommendations
- Time-of-day suggestions
- And more!

---

**Powered by Google Gemini AI** ✨
