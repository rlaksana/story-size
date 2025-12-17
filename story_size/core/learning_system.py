import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

class LearningSystem:
    """Machine learning system for improving platform detection accuracy"""

    def __init__(self):
        self.feedback_file = Path(__file__).parent.parent.parent / "learning_feedback.json"
        self.patterns_file = Path(__file__).parent.parent.parent / "learned_patterns.json"
        self.feedback_data = self._load_feedback()
        self.patterns = self._load_patterns()

    def _load_feedback(self) -> dict:
        """Load existing feedback data"""
        if self.feedback_file.exists():
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "corrections": [],
            "statistics": {
                "total_corrections": 0,
                "accuracy_by_application": {},
                "accuracy_by_pattern": {}
            }
        }

    def _load_patterns(self) -> dict:
        """Load learned patterns"""
        if self.patterns_file.exists():
            with open(self.patterns_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "application_patterns": {},
            "document_patterns": {},
            "platform_associations": {}
        }

    def record_correction(self,
                         doc_text: str,
                         detected_platforms: List[str],
                         correct_platforms: List[str],
                         application_name: Optional[str] = None,
                         user_feedback: Optional[str] = None):
        """Record a correction when AI gets it wrong"""

        correction = {
            "timestamp": datetime.now().isoformat(),
            "doc_snippet": self._extract_snippet(doc_text),
            "detected_platforms": detected_platforms,
            "correct_platforms": correct_platforms,
            "application_name": application_name,
            "user_feedback": user_feedback,
            "key_phrases": self._extract_key_phrases(doc_text),
            "confidence_boost": 0.1  # Will increase with more corrections
        }

        self.feedback_data["corrections"].append(correction)
        self.feedback_data["statistics"]["total_corrections"] += 1

        # Update statistics
        if application_name:
            app_stats = self.feedback_data["statistics"]["accuracy_by_application"]
            if application_name not in app_stats:
                app_stats[application_name] = {"correct": 0, "incorrect": 0}
            app_stats[application_name]["incorrect"] += 1

        self._save_feedback()
        self._update_patterns(correction)

    def _extract_snippet(self, text: str, max_length: int = 200) -> str:
        """Extract relevant snippet from document"""
        # Look for application names, platform indicators
        text_lower = text.lower()
        indicators = ["application:", "app:", "platform:", "affected system:", "system:"]

        for indicator in indicators:
            if indicator in text_lower:
                idx = text_lower.find(indicator)
                start = max(0, idx - 20)
                end = min(len(text), idx + max_length)
                return text[start:end].strip()

        # If no indicators found, return first part
        return text[:max_length] + "..." if len(text) > max_length else text

    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases that might indicate platform"""
        text_lower = text.lower()
        phrases = []

        # Common platform indicators
        patterns = {
            "mobile_applications": ["mobile app", "android", "ios", "flutter", "react native", "apk"],
            "web_applications": ["web application", "browser", "html", "javascript", "react", "angular"],
            "ui_components": ["icon", "button", "navigation", "menu", "screen", "view"],
            "backend_features": ["api", "database", "service", "endpoint", "server"]
        }

        for category, keywords in patterns.items():
            for keyword in keywords:
                if keyword in text_lower:
                    # Extract surrounding context
                    idx = text_lower.find(keyword)
                    context_start = max(0, idx - 30)
                    context_end = min(len(text_lower), idx + len(keyword) + 30)
                    context = text[context_start:context_end]
                    phrases.append({
                        "category": category,
                        "phrase": context,
                        "keyword": keyword
                    })

        return phrases

    def _update_patterns(self, correction: dict):
        """Update learned patterns based on correction"""
        app_name = correction.get("application_name")
        correct_platforms = correction.get("correct_platforms", [])
        detected_platforms = correction.get("detected_platforms", [])

        # Learn application-platform associations
        if app_name and correct_platforms != detected_platforms:
            if app_name not in self.patterns["application_patterns"]:
                self.patterns["application_patterns"][app_name] = {
                    "platforms": correct_platforms,
                    "correction_count": 0,
                    "confidence": 0.5
                }

            self.patterns["application_patterns"][app_name]["platforms"] = correct_platforms
            self.patterns["application_patterns"][app_name]["correction_count"] += 1

            # Increase confidence with more corrections
            count = self.patterns["application_patterns"][app_name]["correction_count"]
            self.patterns["application_patterns"][app_name]["confidence"] = min(0.95, 0.5 + (count * 0.1))

        # Learn from key phrases
        for phrase_data in correction.get("key_phrases", []):
            phrase = phrase_data["phrase"]
            category = phrase_data["category"]

            if phrase not in self.patterns["document_patterns"]:
                self.patterns["document_patterns"][phrase] = {
                    "platforms": {},
                    "count": 0
                }

            for platform in correct_platforms:
                if platform not in self.patterns["document_patterns"][phrase]["platforms"]:
                    self.patterns["document_patterns"][phrase]["platforms"][platform] = 0
                self.patterns["document_patterns"][phrase]["platforms"][platform] += 1

            self.patterns["document_patterns"][phrase]["count"] += 1

        self._save_patterns()

    def get_improved_detection(self, doc_text: str) -> Optional[dict]:
        """Get improved platform detection based on learned patterns"""
        doc_lower = doc_text.lower()

        # Check for known applications
        for app_name, app_data in self.patterns["application_patterns"].items():
            if app_name.lower() in doc_lower:
                return {
                    "platforms": app_data["platforms"],
                    "confidence": app_data["confidence"],
                    "source": f"Learned from {app_data['correction_count']} corrections",
                    "type": "application_match"
                }

        # Check for document patterns
        platform_scores = {}
        for phrase, pattern_data in self.patterns["document_patterns"].items():
            if phrase.lower() in doc_lower:
                for platform, count in pattern_data["platforms"].items():
                    if platform not in platform_scores:
                        platform_scores[platform] = 0
                    platform_scores[platform] += count

        if platform_scores:
            # Normalize scores
            max_score = max(platform_scores.values())
            normalized_scores = {
                platform: score / max_score
                for platform, score in platform_scores.items()
            }

            # Return platforms with score > 0.5
            detected = [p for p, s in normalized_scores.items() if s > 0.5]

            if detected:
                return {
                    "platforms": detected,
                    "confidence": max(normalized_scores.values()),
                    "source": "Learned from document patterns",
                    "type": "pattern_match"
                }

        return None

    def _save_feedback(self):
        """Save feedback data"""
        with open(self.feedback_file, 'w', encoding='utf-8') as f:
            json.dump(self.feedback_data, f, indent=2, ensure_ascii=False)

    def _save_patterns(self):
        """Save learned patterns"""
        with open(self.patterns_file, 'w', encoding='utf-8') as f:
            json.dump(self.patterns, f, indent=2, ensure_ascii=False)

    def get_statistics(self) -> dict:
        """Get learning statistics"""
        return {
            "total_corrections": self.feedback_data["statistics"]["total_corrections"],
            "applications_learned": len(self.patterns["application_patterns"]),
            "patterns_learned": len(self.patterns["document_patterns"]),
            "accuracy_by_app": self.feedback_data["statistics"]["accuracy_by_application"],
            "top_corrected_apps": self._get_top_corrected_apps()
        }

    def _get_top_corrected_apps(self) -> List[dict]:
        """Get applications with most corrections"""
        apps = []
        for app_name, app_data in self.patterns["application_patterns"].items():
            apps.append({
                "name": app_name,
                "corrections": app_data["correction_count"],
                "confidence": app_data["confidence"],
                "platforms": app_data["platforms"]
            })

        return sorted(apps, key=lambda x: x["corrections"], reverse=True)[:5]