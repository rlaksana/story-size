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
            return {
                "detected_platforms": learned_result["platforms"],
                "confidence": learned_result["confidence"],
                "reasoning": f"{learned_result['source']} (confidence: {learned_result['confidence']:.2f})",
                "source": "learned",
                "learned_data": learned_result
            }

        # Then check for known applications from config
        for app_name, app_info in self.context.get("applications", {}).items():
            if app_name.lower() in doc_lower:
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
                        "source": "config"
                    }

        # If no known app found, use pattern matching
        platform_scores = {
            "mobile": self._count_indicators(doc_lower, "mobile_indicators"),
            "frontend": self._count_indicators(doc_lower, "web_indicators"),
            "backend": self._count_indicators(doc_lower, "web_indicators") * 0.8,  # Backend often implied
            "desktop": self._count_indicators(doc_lower, "desktop_indicators")
        }

        # Apply heuristics
        if "human resources" in doc_lower or "hr" in doc_lower:
            # HR systems are commonly web-based
            platform_scores["frontend"] += 0.2
            platform_scores["backend"] += 0.2

        # Determine detected platforms
        detected_platforms = []
        for platform, score in platform_scores.items():
            if score > 0.1:  # Threshold
                detected_platforms.append(platform)

        # Default to frontend+backend if nothing detected
        if not detected_platforms:
            detected_platforms = ["frontend", "backend"]
            confidence = 0.5
            reasoning = "No clear platform indicators detected, defaulting to web application"
        else:
            confidence = min(0.8, max(platform_scores.values()))
            reasoning = f"Detected platforms based on indicators: {detected_platforms}"

        return {
            "detected_platforms": detected_platforms,
            "confidence": confidence,
            "reasoning": reasoning,
            "platform_scores": platform_scores
        }

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