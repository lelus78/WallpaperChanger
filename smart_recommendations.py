"""
Smart Recommendations System using Google Gemini AI
Analyzes user behavior and suggests wallpapers based on preferences
"""
import json
import os
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
from datetime import datetime
import google.generativeai as genai


class SmartRecommendations:
    """AI-powered wallpaper recommendation system"""

    def __init__(self, stats_manager, cache_manager, api_key: Optional[str] = None):
        """
        Initialize the recommendation system

        Args:
            stats_manager: StatisticsManager instance
            cache_manager: CacheManager instance
            api_key: Google Gemini API key
        """
        self.stats_manager = stats_manager
        self.cache_manager = cache_manager
        self.api_key = api_key

        # Configure Gemini if API key is provided
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-2.5-flash')
            except Exception as e:
                print(f"Failed to initialize Gemini: {e}")
                self.model = None
        else:
            self.model = None

    def set_api_key(self, api_key: str) -> bool:
        """
        Set or update the Google Gemini API key

        Args:
            api_key: Google Gemini API key

        Returns:
            True if successful, False otherwise
        """
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            self.api_key = api_key
            return True
        except Exception as e:
            print(f"Failed to set API key: {e}")
            return False

    def analyze_user_preferences(self) -> Dict[str, Any]:
        """
        Analyze user statistics to determine preferences

        Returns:
            Dictionary containing user preference analysis
        """
        wallpapers = self.stats_manager.data.get("wallpapers", {})

        if not wallpapers:
            return {
                "top_tags": [],
                "favorite_colors": [],
                "preferred_providers": [],
                "avg_rating": 0,
                "total_favorites": 0,
                "total_views": 0,
                "time_patterns": {}
            }

        # Collect statistics
        all_tags = []
        all_colors = []
        all_providers = []
        ratings = []
        favorites_count = 0
        total_views = 0
        time_patterns = Counter()

        for path, stats in wallpapers.items():
            # Tags
            all_tags.extend(stats.get("tags", []))

            # Colors - get from cache data
            cache_items = self.cache_manager.list_entries()
            for item in cache_items:
                if item.get("path") == path:
                    primary_color = item.get("primary_color")
                    if primary_color:
                        all_colors.append(primary_color)
                    break

            # Provider
            provider = stats.get("provider")
            if provider:
                all_providers.append(provider)

            # Rating
            rating = stats.get("rating", 0)
            if rating > 0:
                ratings.append(rating)

            # Favorites
            if stats.get("favorite", False):
                favorites_count += 1

            # Views
            views = stats.get("views", 0)
            total_views += views

            # Time patterns
            last_viewed = stats.get("last_viewed")
            if last_viewed:
                try:
                    dt = datetime.fromisoformat(last_viewed)
                    hour = dt.hour
                    if 6 <= hour < 12:
                        time_patterns["morning"] += 1
                    elif 12 <= hour < 18:
                        time_patterns["afternoon"] += 1
                    elif 18 <= hour < 22:
                        time_patterns["evening"] += 1
                    else:
                        time_patterns["night"] += 1
                except:
                    pass

        # Calculate top preferences
        tag_counter = Counter(all_tags)
        color_counter = Counter(all_colors)
        provider_counter = Counter(all_providers)

        return {
            "top_tags": tag_counter.most_common(10),
            "favorite_colors": color_counter.most_common(5),
            "preferred_providers": provider_counter.most_common(3),
            "avg_rating": sum(ratings) / len(ratings) if ratings else 0,
            "total_favorites": favorites_count,
            "total_views": total_views,
            "time_patterns": dict(time_patterns)
        }

    def get_recommendations(self, count: int = 12) -> List[Dict[str, Any]]:
        """
        Get wallpaper recommendations based on user preferences

        Args:
            count: Number of recommendations to return

        Returns:
            List of recommended wallpapers with scores and reasons
        """
        preferences = self.analyze_user_preferences()
        cache_items = self.cache_manager.list_entries()
        wallpapers_stats = self.stats_manager.data.get("wallpapers", {})

        # Score each wallpaper
        scored_wallpapers = []

        for item in cache_items:
            path = item.get("path")

            # Skip banned wallpapers
            if self.stats_manager.is_banned(path):
                continue

            stats = wallpapers_stats.get(path, {})
            score = 0
            reasons = []

            # Factor 1: Favorite tags (40% weight)
            item_tags = set(stats.get("tags", []))
            top_tags = {tag for tag, _ in preferences["top_tags"][:5]}
            matching_tags = item_tags & top_tags
            if matching_tags:
                tag_score = len(matching_tags) * 40 / len(top_tags) if top_tags else 0
                score += tag_score
                if tag_score > 0:
                    reasons.append(f"Matches preferred tags: {', '.join(list(matching_tags)[:2])}")

            # Factor 2: Favorite colors (20% weight)
            primary_color = item.get("primary_color", "")
            favorite_colors = {color for color, _ in preferences["favorite_colors"][:3]}
            if primary_color in favorite_colors:
                score += 20
                reasons.append(f"Preferred color: {primary_color}")

            # Factor 3: Preferred provider (15% weight)
            provider = item.get("provider", "")
            preferred_providers = {prov for prov, _ in preferences["preferred_providers"][:2]}
            if provider in preferred_providers:
                score += 15
                reasons.append(f"From preferred provider: {provider}")

            # Factor 4: Rating similarity (15% weight)
            rating = stats.get("rating", 0)
            if preferences["avg_rating"] > 0:
                if rating >= preferences["avg_rating"]:
                    score += 15
                    if rating > 0:
                        reasons.append(f"High rating: {rating} stars")

            # Factor 5: Not viewed recently (10% weight)
            views = stats.get("views", 0)
            if views == 0:
                score += 10
                reasons.append("New wallpaper")
            elif views < 3:
                score += 5
                reasons.append("Rarely viewed")

            # Only include wallpapers with some score
            if score > 0:
                scored_wallpapers.append({
                    "item": item,
                    "score": score,
                    "reasons": reasons,
                    "stats": stats
                })

        # Sort by score
        scored_wallpapers.sort(key=lambda x: x["score"], reverse=True)

        return scored_wallpapers[:count]

    def get_ai_suggestions(self, user_preferences: Dict[str, Any]) -> Optional[str]:
        """
        Use Gemini AI to generate intelligent suggestions

        Args:
            user_preferences: Dictionary of analyzed user preferences

        Returns:
            AI-generated suggestion text or None if API is not configured
        """
        if not self.model:
            return None

        try:
            prompt = f"""Based on these wallpaper preferences, suggest 3 new search queries to find similar wallpapers:

User Preferences:
- Favorite Tags: {', '.join([tag for tag, _ in user_preferences['top_tags'][:5]])}
- Favorite Colors: {', '.join([color for color, _ in user_preferences['favorite_colors'][:3]])}
- Average Rating: {user_preferences['avg_rating']:.1f}/5
- Time Patterns: {user_preferences['time_patterns']}

Provide exactly 3 search queries that would help find wallpapers matching these preferences.
Format: One query per line, no numbering or extra text."""

            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Gemini API error: {e}")
            return None

    def suggest_search_queries(self) -> List[str]:
        """
        Suggest new search queries based on user preferences

        Returns:
            List of suggested search queries
        """
        preferences = self.analyze_user_preferences()

        # Use AI if available
        if self.model:
            ai_suggestions = self.get_ai_suggestions(preferences)
            if ai_suggestions:
                # Parse AI response into list
                queries = [q.strip() for q in ai_suggestions.split('\n') if q.strip()]
                return queries[:3]

        # Fallback: rule-based suggestions
        queries = []
        top_tags = [tag for tag, _ in preferences["top_tags"][:5]]

        if len(top_tags) >= 2:
            queries.append(f"{top_tags[0]} {top_tags[1]}")
        if len(top_tags) >= 3:
            queries.append(f"{top_tags[1]} {top_tags[2]} minimalist")
        if preferences["favorite_colors"]:
            color = preferences["favorite_colors"][0][0]
            if top_tags:
                queries.append(f"{color} {top_tags[0]}")

        return queries[:3]

    def detect_mood_and_suggest(self, current_weather: Optional[str] = None) -> Dict[str, Any]:
        """
        🎭 AI MOOD DETECTION - Detect current mood based on time, weather, and usage patterns

        Args:
            current_weather: Current weather condition (optional)

        Returns:
            Dictionary with mood analysis and wallpaper suggestions
        """
        if not self.model:
            return {"mood": "neutral", "suggestions": [], "reason": "AI not configured"}

        try:
            # Get current context
            now = datetime.now()
            hour = now.hour
            day_of_week = now.strftime("%A")
            preferences = self.analyze_user_preferences()

            # Build context for AI
            prompt = f"""Analyze the current context and suggest a mood for wallpaper selection:

Current Context:
- Time: {now.strftime("%H:%M")} ({hour}:00)
- Day: {day_of_week}
- Weather: {current_weather or "Unknown"}

User Preferences:
- Favorite Tags: {', '.join([tag for tag, _ in preferences['top_tags'][:5]])}
- Time Patterns: {preferences['time_patterns']}
- Favorite Colors: {', '.join([color for color, _ in preferences['favorite_colors'][:3]])}

Based on this context, suggest:
1. Current mood (one word: energetic/calm/focused/creative/relaxed)
2. Recommended wallpaper style (brief description)
3. Three search queries that match this mood

Format your response as:
MOOD: [mood]
STYLE: [style description]
QUERY1: [search query 1]
QUERY2: [search query 2]
QUERY3: [search query 3]"""

            response = self.model.generate_content(prompt)
            result = response.text.strip()

            # Parse AI response
            lines = result.split('\n')
            mood = "neutral"
            style = ""
            queries = []

            for line in lines:
                if line.startswith("MOOD:"):
                    mood = line.replace("MOOD:", "").strip().lower()
                elif line.startswith("STYLE:"):
                    style = line.replace("STYLE:", "").strip()
                elif line.startswith("QUERY"):
                    query = line.split(":", 1)[1].strip() if ":" in line else ""
                    if query:
                        queries.append(query)

            return {
                "mood": mood,
                "style": style,
                "queries": queries[:3],
                "reason": f"AI detected {mood} mood based on {day_of_week} {hour}:00"
            }

        except Exception as e:
            print(f"Mood detection error: {e}")
            return {"mood": "neutral", "suggestions": [], "reason": str(e)}

    def analyze_wallpaper_with_ai(self, wallpaper_path: str, tags: List[str]) -> Dict[str, Any]:
        """
        📝 AI WALLPAPER ANALYSIS - Generate creative description and enhanced tags

        Args:
            wallpaper_path: Path to wallpaper image
            tags: Existing tags for the wallpaper

        Returns:
            Dictionary with AI-generated description, mood, and suggested tags
        """
        if not self.model:
            return {"description": "", "mood": "", "suggested_tags": [], "style": ""}

        try:
            prompt = f"""Analyze this wallpaper based on its existing tags and create an enhanced description:

Existing Tags: {', '.join(tags[:10])}

Provide:
1. A creative, poetic description (2-3 sentences)
2. The overall mood/feeling it evokes (one word)
3. Art style category (e.g., minimalist, photorealistic, abstract, etc.)
4. 5 additional relevant tags that aren't in the existing list

Format:
DESCRIPTION: [your description]
MOOD: [mood]
STYLE: [art style]
TAGS: [tag1, tag2, tag3, tag4, tag5]"""

            response = self.model.generate_content(prompt)
            result = response.text.strip()

            # Parse response
            lines = result.split('\n')
            description = ""
            mood = ""
            style = ""
            suggested_tags = []

            for line in lines:
                if line.startswith("DESCRIPTION:"):
                    description = line.replace("DESCRIPTION:", "").strip()
                elif line.startswith("MOOD:"):
                    mood = line.replace("MOOD:", "").strip().lower()
                elif line.startswith("STYLE:"):
                    style = line.replace("STYLE:", "").strip()
                elif line.startswith("TAGS:"):
                    tags_str = line.replace("TAGS:", "").strip()
                    suggested_tags = [t.strip() for t in tags_str.split(',')]

            return {
                "description": description,
                "mood": mood,
                "style": style,
                "suggested_tags": suggested_tags[:5]
            }

        except Exception as e:
            print(f"Wallpaper analysis error: {e}")
            return {"description": "", "mood": "", "suggested_tags": [], "style": ""}

    def natural_language_search(self, query: str) -> List[Dict[str, Any]]:
        """
        💬 AI NATURAL LANGUAGE SEARCH - Search using conversational language

        Args:
            query: Natural language search query (e.g., "something relaxing for evening")

        Returns:
            List of matching wallpapers with AI reasoning
        """
        if not self.model:
            return []

        try:
            # Get available wallpapers
            cache_items = self.cache_manager.list_entries()
            wallpapers_stats = self.stats_manager.data.get("wallpapers", {})

            # Build wallpaper database for AI
            wallpaper_descriptions = []
            for idx, item in enumerate(cache_items[:50]):  # Limit to 50 for performance
                path = item.get("path")
                if self.stats_manager.is_banned(path):
                    continue

                stats = wallpapers_stats.get(path, {})
                tags = stats.get("tags", [])
                color = item.get("primary_color", "")
                provider = item.get("provider", "")

                wallpaper_descriptions.append(
                    f"{idx}: {provider} - {color} - tags: {', '.join(tags[:5])}"
                )

            # Ask AI to match query with wallpapers
            prompt = f"""User is searching for wallpapers with this natural language query:
"{query}"

Available wallpapers:
{chr(10).join(wallpaper_descriptions[:30])}

Select the top 5 wallpaper numbers (0-{len(wallpaper_descriptions)-1}) that best match the user's request.
Also explain why each matches.

Format:
NUMBER: [wallpaper number] - REASON: [why it matches]

Provide exactly 5 matches."""

            response = self.model.generate_content(prompt)
            result = response.text.strip()

            # Parse AI response
            matches = []
            for line in result.split('\n'):
                if 'NUMBER:' in line and 'REASON:' in line:
                    try:
                        parts = line.split('REASON:')
                        number_part = parts[0].replace('NUMBER:', '').strip()
                        reason = parts[1].strip() if len(parts) > 1 else "AI matched"

                        idx = int(''.join(filter(str.isdigit, number_part.split('-')[0])))
                        if 0 <= idx < len(cache_items):
                            matches.append({
                                "item": cache_items[idx],
                                "reason": reason,
                                "score": 100 - len(matches) * 10  # Decreasing score
                            })
                    except:
                        continue

            return matches[:5]

        except Exception as e:
            print(f"Natural language search error: {e}")
            return []

    def predict_next_wallpaper(self) -> Optional[Dict[str, Any]]:
        """
        🔮 AI PREDICTIVE SELECTION - Predict which wallpaper user wants next

        Returns:
            Predicted wallpaper with AI reasoning
        """
        if not self.model:
            return None

        try:
            now = datetime.now()
            hour = now.hour
            preferences = self.analyze_user_preferences()

            # Build prediction context
            prompt = f"""Predict the best wallpaper for this user right now:

Time: {hour}:00
User History:
- Most viewed time: {max(preferences['time_patterns'].items(), key=lambda x: x[1])[0] if preferences['time_patterns'] else 'unknown'}
- Favorite tags: {', '.join([tag for tag, _ in preferences['top_tags'][:3]])}
- Favorite colors: {', '.join([color for color, _ in preferences['favorite_colors'][:2]])}

What type of wallpaper would be perfect right now? Consider:
- Time of day and typical mood
- User's historical preferences
- Seasonal appropriateness

Respond with ONE line describing the ideal wallpaper:
[description]"""

            response = self.model.generate_content(prompt)
            prediction = response.text.strip()

            # Find best matching wallpaper based on AI prediction
            recommendations = self.get_recommendations(count=5)

            if recommendations:
                best_match = recommendations[0]
                best_match['ai_prediction'] = prediction
                return best_match

            return None

        except Exception as e:
            print(f"Prediction error: {e}")
            return None

    def get_similar_wallpapers(self, reference_path: str, count: int = 6) -> List[Dict[str, Any]]:
        """
        🎨 AI STYLE SIMILARITY - Find wallpapers similar to a reference

        Args:
            reference_path: Path to reference wallpaper
            count: Number of similar wallpapers to return

        Returns:
            List of similar wallpapers with similarity scores
        """
        if not self.model:
            return []

        try:
            # Get reference wallpaper info
            wallpapers_stats = self.stats_manager.data.get("wallpapers", {})
            ref_stats = wallpapers_stats.get(reference_path, {})
            ref_tags = ref_stats.get("tags", [])

            cache_items = self.cache_manager.list_entries()
            ref_item = None
            for item in cache_items:
                if item.get("path") == reference_path:
                    ref_item = item
                    break

            if not ref_item:
                return []

            ref_color = ref_item.get("primary_color", "")
            ref_provider = ref_item.get("provider", "")

            # Ask AI to find similar styles
            prompt = f"""Find wallpapers with similar style to this reference:

Reference:
- Tags: {', '.join(ref_tags[:10])}
- Color: {ref_color}
- Provider: {ref_provider}

Describe what makes a wallpaper "similar" to this one (style, mood, composition).
One short sentence:"""

            response = self.model.generate_content(prompt)
            similarity_criteria = response.text.strip()

            # Score wallpapers based on similarity
            similar_wallpapers = []
            ref_tags_set = set(ref_tags)

            for item in cache_items:
                path = item.get("path")
                if path == reference_path or self.stats_manager.is_banned(path):
                    continue

                stats = wallpapers_stats.get(path, {})
                item_tags = set(stats.get("tags", []))
                item_color = item.get("primary_color", "")

                # Calculate similarity score
                score = 0
                # Tag overlap
                tag_overlap = len(ref_tags_set & item_tags)
                score += tag_overlap * 20

                # Color match
                if item_color == ref_color:
                    score += 30

                # Provider match (same source often similar style)
                if item.get("provider") == ref_provider:
                    score += 10

                if score > 0:
                    similar_wallpapers.append({
                        "item": item,
                        "score": score,
                        "similarity_reason": similarity_criteria,
                        "matching_tags": list(ref_tags_set & item_tags)[:3]
                    })

            # Sort by score
            similar_wallpapers.sort(key=lambda x: x["score"], reverse=True)

            return similar_wallpapers[:count]

        except Exception as e:
            print(f"Similarity search error: {e}")
            return []
