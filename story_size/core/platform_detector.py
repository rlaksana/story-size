import json
import os
from typing import Dict, List, Optional
import re
from .learning_system import LearningSystem

class PlatformDetector:
    """Smart platform detection with application context"""

    def __init__(self):
        self.context_file = os.path.join(os.path.dirname(__file__), "../../application_context.json")
        self.context = self._load_context()
        self.learning_system = LearningSystem()

    def _load_context(self) -> dict:
        """Load application context from JSON file"""
        try:
            with open(self.context_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Default context if file doesn't exist
            return {
                "applications": {},
                "platform_patterns": {
                    "mobile_indicators": ["mobile app", "android", "ios", "flutter", "react native"],
                    "web_indicators": ["web application", "browser", "html", "javascript"],
                    "desktop_indicators": ["desktop", "windows application", "electron"]
                }
            }

    def detect_platform_from_context(self, doc_text: str) -> Dict[str, any]:
        """Detect platforms based on document text and known application context"""
        doc_lower = doc_text.lower()

        # First check learned patterns (higher priority as they're based on corrections)
        learned_result = self.learning_system.get_improved_detection(doc_text)
        if learned_result and learned_result.get("confidence", 0) > 0.7:
            result = {
                "detected_platforms": learned_result["platforms"],
                "confidence": learned_result["confidence"],
                "reasoning": f"{learned_result['source']} (confidence: {learned_result['confidence']:.2f})",
                "source": "learned",
                "learned_data": learned_result
            }

            # If this is a learned application pattern, also add guaranteed platforms from config
            if learned_result.get("type") == "application_match":
                # Find the app name from the learned result
                for app_name, app_data in self.learning_system.patterns.get("application_patterns", {}).items():
                    if app_data["platforms"] == learned_result["platforms"]:
                        # Found the app, get guaranteed platforms from config
                        app_config = self.context.get("applications", {}).get(app_name)
                        if app_config:
                            result["guaranteed_platforms"] = app_config.get("guaranteed_platforms", app_config["platforms"])
                            result["application_match"] = app_name
                            result["all_documented_platforms"] = app_config.get("all_platforms", app_config["platforms"])
                        break

            return result

        # Then check for known applications from config
        for app_name, app_info in self.context.get("applications", {}).items():
            # Check both full name and abbreviations (from indicators)
            search_terms = [app_name.lower()]
            # Add common abbreviations from indicators
            for indicator in app_info.get("indicators", []):
                if "(" in indicator and ")" in indicator:
                    # This is an abbreviation like "(AC)"
                    search_terms.append(indicator.lower())

            # Check if any search term is in the document
            if any(term in doc_lower for term in search_terms):
                # Check if we have learned corrections for this app
                app_patterns = self.learning_system.patterns.get("application_patterns", {})
                if app_name in app_patterns:
                    learned_platforms = app_patterns[app_name]["platforms"]
                    learned_confidence = app_patterns[app_name]["confidence"]
                    return {
                        "detected_platforms": learned_platforms,
                        "confidence": learned_confidence,
                        "reasoning": f"Learned from {app_patterns[app_name]['correction_count']} corrections that '{app_name}' uses: {', '.join(learned_platforms)}",
                        "application_match": app_name,
                        "source": "learned_application"
                    }
                else:
                    return {
                        "detected_platforms": app_info["platforms"],
                        "confidence": 0.9,
                        "reasoning": f"Recognized application '{app_name}' which is a {app_info['type']} application",
                        "application_match": app_name,
                        "source": "config",
                        "all_documented_platforms": app_info.get("all_platforms", app_info["platforms"])  # ALL platforms this app uses
                    }

        # If no known app found, use pattern matching
        platform_scores = {
            "mobile": self._count_indicators(doc_lower, "mobile_indicators"),
            "frontend": self._count_indicators(doc_lower, "web_indicators"),
            "backend": self._count_indicators(doc_lower, "web_indicators") * 0.8,  # Backend often implied
        }

        # Determine detected platforms
        detected_platforms = []
        for platform, score in platform_scores.items():
            if score > 0.1:  # Threshold
                detected_platforms.append(platform)

        # Check for abbreviations to provide application context
        application_match = None
        for app_name, app_info in self.context.get("applications", {}).items():
            for indicator in app_info.get("indicators", []):
                if "(" in indicator and ")" in indicator:
                    if indicator.lower() in doc_lower:
                        application_match = app_name
                        # Add the app's platforms to detected_platforms as context
                        for app_platform in app_info["platforms"]:
                            if app_platform not in detected_platforms:
                                detected_platforms.append(app_platform)
                        break
            if application_match:
                break

        # Default to frontend+backend if nothing detected
        if not detected_platforms:
            detected_platforms = ["frontend", "backend"]
            confidence = 0.5
            reasoning = "No clear platform indicators detected, defaulting to web application"
        else:
            confidence = min(0.8, max(platform_scores.values()))
            if application_match:
                reasoning = f"Detected '{application_match}' via abbreviation, using platforms: {detected_platforms}"
            else:
                reasoning = f"Detected platforms based on indicators: {detected_platforms}"

        result = {
            "detected_platforms": detected_platforms,
            "confidence": confidence,
            "reasoning": reasoning,
            "platform_scores": platform_scores
        }

        # Add application match if found via abbreviation
        if application_match:
            result["application_match"] = application_match
            result["source"] = "config_abbreviation"
            result["all_documented_platforms"] = self.context.get("applications", {}).get(application_match, {}).get("all_platforms", detected_platforms)

        return result

    def _count_indicators(self, text: str, indicator_type: str) -> float:
        """Count how many platform indicators appear in text"""
        indicators = self.context.get("platform_patterns", {}).get(indicator_type, [])
        count = 0
        for indicator in indicators:
            if indicator in text:
                count += 1
        return count / len(indicators) if indicators else 0

    def enhance_ai_prompt(self, base_prompt: str, doc_text: str) -> str:
        """Enhance AI prompt with application context"""
        context_info = self.detect_platform_from_context(doc_text)

        context_addition = f"""

APPLICATION CONTEXT:
{context_info['reasoning']}

Based on the document analysis:
- Likely platforms: {', '.join(context_info['detected_platforms'])}
- Confidence: {context_info['confidence']}

IMPORTANT: When determining platforms, prioritize this context over generic assumptions.
- If a known application is mentioned, use its documented platform.
- Don't default to web/frontend just because UI changes are mentioned.
- Consider the full context of the work item.

"""

        return base_prompt + context_addition