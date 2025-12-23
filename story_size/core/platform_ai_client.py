import os
import json
import requests
from typing import Dict, Optional
from story_size.core.models import (
    PlatformDetection, PlatformAnalysis, CompleteAnalysis,
    PlatformRequirement, EnhancedCodeAnalysis
)
from story_size.core.platform_detector import PlatformDetector

class PlatformAwareAIClient:
    def __init__(self, config_data: dict):
        self.config_data = config_data
        self.llm_config = config_data.get("llm", {})
        self.api_key_env = self.llm_config.get("api_key_env", "ZAI_API_KEY")
        self.api_key = os.environ.get(self.api_key_env)
        self.platform_detector = PlatformDetector()

        if not self.api_key:
            raise ValueError(f"API key not found in environment variable: {self.api_key_env}")

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "anthropic-version": "2023-06-01",
        }

    async def detect_platforms(self, doc_summary: str, code_analysis: EnhancedCodeAnalysis, force_platforms: Optional[str] = None) -> PlatformDetection:
        """Stage 1: Detect required platforms"""

        platform_structure = self._generate_platform_structure_analysis(code_analysis)

        # Get application context
        app_context = self.platform_detector.detect_platform_from_context(doc_summary)

        system_prompt = """
Analyze this work item and available codebase structure.

TASK: Determine which platforms are needed and assess complexity.

AVAILABLE CODE STRUCTURE:
{platform_structure}

{app_context}

PLATFORMS TO CONSIDER:
- Frontend (UI/UX, web application, components) - Use for web-based interfaces
- Backend (API, services, database, business logic) - Use for server-side logic
- Mobile (iOS/Android apps, cross-platform) - Use for native mobile applications
- DevOps/Infrastructure (deployment, CI/CD, infrastructure) - Use for deployment/ops changes

IMPORTANT GUIDELINES:
1. If a known application is mentioned (like "Andal Connect" or "Andal Kharisma"), use its documented platform
2. Don't default to frontend just because UI changes are mentioned - check if it's a mobile app
3. Consider the full context of the work item
4. Backend is required for any data-driven features, even in mobile apps

WORK ITEM TYPES:
- feature: New functionality
- bugfix: Fix defects
- enhancement: Improve existing functionality
- refactor: Code restructuring
- research: Investigation/POC

COMPLEXITY LEVELS:
- simple: Straightforward implementation
- moderate: Some complexity or integration
- complex: Multiple systems or complex logic
- very_complex: High complexity, high risk

RESPONSE FORMAT (JSON):
{{
  "platform_requirements": {{
    "frontend": {{"required": true, "scope": "high|medium|low", "technologies": ["react", "typescript"]}},
    "backend": {{"required": true, "scope": "high|medium|low", "technologies": ["dotnet", "sql"]}},
    "mobile": {{"required": false, "scope": "high|medium|low", "technologies": ["flutter", "dart"]}},
    "devops": {{"required": true, "scope": "high|medium|low", "technologies": ["docker", "k8s"]}}
  }},
  "work_item_type": "feature|bugfix|enhancement|refactor|research",
  "complexity_level": "simple|moderate|complex|very_complex",
  "estimated_platforms": ["frontend", "backend"],
  "confidence": 0.85,
  "reasoning": "Detailed explanation of why these platforms are needed based on the work item"
}}

Work Item Documents:
---
{doc_summary}
---
"""

        user_prompt = system_prompt.format(
            platform_structure=platform_structure,
            app_context=f"APPLICATION CONTEXT:\n{app_context['reasoning']}\nLikely platforms: {', '.join(app_context['detected_platforms'])}",
            doc_summary=doc_summary
        )

        # Override platforms if force_platforms is specified
        if force_platforms:
            forced_platforms = [p.strip().lower() for p in force_platforms.split(',')]

            # Add override instruction to prompt
            user_prompt += f"\n\nIMPORTANT OVERRIDE: The user has specified that this work item is for these platforms ONLY: {', '.join(forced_platforms)}. "
            user_prompt += "Ignore any automatic detection and use these exact platforms."

        response_data = await self._call_llm(user_prompt)

        # Parse platform requirements
        platform_requirements = {}
        for platform, req_data in response_data["platform_requirements"].items():
            platform_requirements[platform] = PlatformRequirement(**req_data)

        # Apply force_platforms override if specified
        if force_platforms:
            forced_platforms = [p.strip().lower() for p in force_platforms.split(',')]

            # Reset all platforms to not required
            for platform in platform_requirements:
                platform_requirements[platform].required = False

            # Set forced platforms as required
            platform_mapping = {
                'frontend': 'frontend',
                'backend': 'backend',
                'mobile': 'mobile',
                'devops': 'devops'
            }

            for forced_platform in forced_platforms:
                if forced_platform in platform_mapping:
                    platform_name = platform_mapping[forced_platform]
                    if platform_name in platform_requirements:
                        platform_requirements[platform_name].required = True

            # Update estimated platforms
            response_data["estimated_platforms"] = forced_platforms
            response_data["confidence"] = 1.0  # Maximum confidence when forced
            response_data["reasoning"] = f"Platforms forced by user: {', '.join(forced_platforms)}"

        return PlatformDetection(
            platform_requirements=platform_requirements,
            work_item_type=response_data["work_item_type"],
            complexity_level=response_data["complexity_level"],
            estimated_platforms=response_data["estimated_platforms"],
            confidence=response_data["confidence"],
            reasoning=response_data["reasoning"]
        )

    async def analyze_platform(self,
                             platform: str,
                             doc_summary: str,
                             code_analysis: EnhancedCodeAnalysis,
                             platform_detection: PlatformDetection,
                             image_analysis: dict = None) -> PlatformAnalysis:
        """Stage 2: Detailed platform-specific analysis"""

        # Get platform-specific code summary
        platform_summary = code_analysis.platform_summaries.get(platform)

        if not platform_summary or platform_summary.files_estimated == 0:
            # Return empty analysis for platforms without code
            return PlatformAnalysis(
                platform=platform,
                factors={},
                explanation=f"No {platform} code detected in the repository.",
                recommended_approach="",
                estimated_hours={"min": 0, "max": 0},
                key_components=[],
                key_challenges=[]
            )

        platform_prompt = self._get_platform_specific_prompt(platform)
        platform_context = self._generate_platform_context(platform_summary, platform)

        # Add image context if available
        image_context = ""
        if image_analysis and image_analysis.get('total_images', 0) > 0:
            indicators = image_analysis.get('complexity_indicators', {})
            image_context = f"""
VISUAL ELEMENTS ANALYSIS:
========================
Total images analyzed: {image_analysis.get('total_images', 0)}
Images with extracted text: {image_analysis.get('images_with_text', 0)}
Total OCR characters extracted: {image_analysis.get('total_ocr_chars', 0)}
Visual Complexity Score: {image_analysis.get('total_image_complexity', 0)} (0-5 scale)

Visual Elements Detected:
• Diagrams/Charts: {indicators.get('has_diagrams', False)}
• Tables: {indicators.get('has_tables', False)}
• Screenshots: {indicators.get('has_screenshots', False)}
• Forms: {indicators.get('has_forms', False)}
• Workflows: {indicators.get('has_workflows', False)}
• Icons/UI Elements: {indicators.get('has_icons', False)}

IMPORTANT for {platform.upper()} analysis:
- Diagrams and workflows represent complex business logic that needs {platform} implementation
- Screenshots suggest UI changes or system integrations affecting {platform}
- Forms indicate user input validation requirements for {platform}
- Tables may imply data structure modifications affecting {platform}
- Multiple visual elements increase coordination needs for {platform} development
"""

        system_prompt = f"""
Analyze this {platform} work item with detailed code context.

{platform_prompt}

WORK ITEM:
{doc_summary}

{platform.upper()} CODEBASE CONTEXT:
{platform_context}

{image_context}

TASK: Provide detailed {platform} complexity analysis and recommendations.

Focus on:
- Technical complexity specific to {platform}
- Integration challenges
- Key components that need modification
- Implementation approach
- Potential risks and challenges

Response format (JSON):
{{
  "factors": {{
    {self._get_platform_factors_template(platform)}
  }},
  "explanation": "Detailed explanation of {platform} complexity and approach",
  "recommended_approach": "Specific technical approach and tools",
  "estimated_hours": {{"min": 16, "max": 24}},
  "key_components": ["Component1", "Component2"],
  "key_challenges": ["Challenge1", "Challenge2"]
}}
"""

        response_data = await self._call_llm(system_prompt)

        return PlatformAnalysis(
            platform=platform,
            factors=response_data["factors"],
            explanation=response_data["explanation"],
            recommended_approach=response_data["recommended_approach"],
            estimated_hours=response_data["estimated_hours"],
            key_components=response_data.get("key_components", []),
            key_challenges=response_data.get("key_challenges", [])
        )

    async def get_complete_analysis(self,
                                  doc_summary: str,
                                  code_analysis: EnhancedCodeAnalysis,
                                  force_platforms: Optional[str] = None,
                                  image_analysis: dict = None) -> CompleteAnalysis:
        """Run both stages and return combined results"""

        try:
            # Stage 1: Detect platforms
            # Check if we have image analysis to include
            if image_analysis and image_analysis.get('total_images', 0) > 0:
                print(f"[INFO] Processing with image analysis: {image_analysis.get('total_images')} images found")

            print("Stage 1: Detecting required platforms...")
            platform_detection = await self.detect_platforms(doc_summary, code_analysis, force_platforms)

            print(f"Platforms detected: {', '.join(platform_detection.estimated_platforms)}")
            print(f"Work item type: {platform_detection.work_item_type}")
            print(f"Complexity level: {platform_detection.complexity_level}")

            # Stage 2: Analyze each required platform
            platform_analyses = {}
            for platform in platform_detection.estimated_platforms:
                print(f"Stage 2: Analyzing {platform}...")
                platform_analyses[platform] = await self.analyze_platform(
                    platform, doc_summary, code_analysis, platform_detection, image_analysis
                )
                print(f"{platform} analysis complete")

            # Calculate story points
            story_points_data = await self._calculate_story_points(platform_analyses, platform_detection)

            return CompleteAnalysis(
                platform_detection=platform_detection,
                platform_analyses=platform_analyses,
                overall_story_points=story_points_data["overall"],
                platform_story_points=story_points_data["by_platform"],
                confidence_score=platform_detection.confidence
            )

        except Exception as e:
            print(f"Platform-aware analysis failed: {e}")
            # Re-raise the exception since traditional fallback is removed
            raise Exception(f"Platform-aware analysis failed and no fallback available: {e}")

    def _generate_platform_structure_analysis(self, code_analysis: EnhancedCodeAnalysis) -> str:
        """Generate structured analysis of available platform code with project tree"""

        structure_lines = []
        if code_analysis.platform_summaries:
            for platform, summary in code_analysis.platform_summaries.items():
                if summary.files_estimated > 0:
                    structure_lines.append(f"[PLATFORM] {platform.upper()}:")
                    structure_lines.append(f"  - Files: {summary.files_estimated}")
                    structure_lines.append(f"  - Languages: {', '.join(summary.languages_detected)}")
                    structure_lines.append(f"  - Key Files: {', '.join(summary.key_files[:3])}")
                    if summary.complexity_indicators:
                        loc = summary.complexity_indicators.get("total_loc", 0)
                        structure_lines.append(f"  - Lines of Code: {loc}")

                    # Add project tree for better AI context
                    if summary.project_tree:
                        structure_lines.append(f"  - Project Structure:")
                        for tree_line in summary.project_tree.split("\n"):
                            structure_lines.append(f"    {tree_line}")

                    structure_lines.append("")

        return "\n".join(structure_lines) if structure_lines else "No platform-specific code detected."

    def _generate_platform_context(self, platform_summary, platform: str) -> str:
        """Generate platform-specific code context"""

        context_lines = [
            f"Platform: {platform.upper()}",
            f"Files: {platform_summary.files_estimated}",
            f"Languages: {', '.join(platform_summary.languages_detected)}",
            f"Directory: {platform_summary.directory}"
        ]

        if platform_summary.key_files:
            context_lines.append(f"Key Files: {', '.join(platform_summary.key_files[:5])}")

        if platform_summary.loc_by_language:
            loc_info = [f"{lang}: {loc} LOC" for lang, loc in platform_summary.loc_by_language.items()]
            context_lines.append(f"Lines of Code by Language: {', '.join(loc_info)}")

        if platform_summary.complexity_indicators:
            indicators = platform_summary.complexity_indicators
            if indicators.get("large_files"):
                total_large = sum(indicators["large_files"].values())
                context_lines.append(f"Large Files (>500 lines): {total_large}")

        return "\n".join(context_lines)

    def _get_platform_specific_prompt(self, platform: str) -> str:
        """Get platform-specific analysis prompt"""

        prompts = {
            "frontend": """
FRONTEND ANALYSIS FACTORS:
- UI Complexity: Component complexity, state management, visual design
- User Interaction: Forms, validation, user flows, accessibility
- Performance: Rendering optimization, lazy loading, bundle size
- Integration: API integration, third-party services, routing
- Testing: Unit tests, integration tests, E2E testing needs
            """,

            "backend": """
BACKEND ANALYSIS FACTORS:
- Business Logic: Domain complexity, validation rules, business workflows
- Database Impact: Schema changes, migrations, query complexity
- API Design: Endpoint complexity, request/response models, documentation
- Integration: External services, message queues, caching
- Security & Performance: Authentication, authorization, optimization
            """,

            "mobile": """
MOBILE ANALYSIS FACTORS:
- Platform Complexity: Native features, platform-specific UI/UX
- Offline Support: Local storage, sync capabilities, conflict resolution
- Device Integration: Camera, GPS, push notifications, biometrics
- App Store Requirements: Submission complexity, review considerations
- Cross-Platform: Framework complexity, platform differences
            """,

            "devops": """
DEVOPS ANALYSIS FACTORS:
- Infrastructure: Server setup, networking, load balancing
- Automation: CI/CD pipelines, automated testing, deployment scripts
- Deployment: Containerization, orchestration, environment management
- Monitoring: Logging, metrics, alerting, health checks
- Security: Access control, secrets management, compliance
            """
        }

        return prompts.get(platform, "Analyze this platform for technical complexity.")

    def _get_platform_factors_template(self, platform: str) -> str:
        """Get platform-specific factors JSON template"""

        templates = {
            "frontend": '"ui_complexity": 3, "user_interaction": 4, "performance": 2, "integration": 3, "testing": 3',
            "backend": '"business_logic": 4, "database_impact": 3, "api_design": 3, "integration": 2, "security_performance": 4',
            "mobile": '"platform_complexity": 4, "offline_support": 3, "device_integration": 2, "app_store_requirements": 2, "cross_platform": 3',
            "devops": '"infrastructure": 3, "automation": 4, "deployment": 3, "monitoring": 2, "security": 3'
        }

        return templates.get(platform, '"complexity": 3')

    async def _call_llm(self, prompt: str) -> dict:
        """Call the LLM API with error handling"""

        data = {
            "model": self.llm_config.get("model", "glm-4.6"),
            "system": "You are an expert software architect analyzing technical requirements. Return ONLY valid JSON without any additional text or formatting.",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1500,
            "temperature": 0.2,
        }

        try:
            response = requests.post(
                self.llm_config.get("endpoint"),
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()

            # Handle different response structures
            if 'content' in result and len(result['content']) > 0:
                content_str = result['content'][0]['text']
            elif 'choices' in result and len(result['choices']) > 0:
                content_str = result['choices'][0]['message']['content']
            else:
                raise RuntimeError(f"Unexpected response structure: {result}")

            # Clean up the JSON response
            content_str = content_str.strip()

            # Handle JSON wrapped in code blocks
            if "```json" in content_str:
                content_str = content_str.split("```json")[1].split("```")[0]
            elif "```" in content_str:
                content_str = content_str.split("```")[1].split("```")[0]

            # Remove any leading/trailing whitespace and newlines
            content_str = content_str.strip()

            # Find JSON object boundaries
            if content_str.startswith('{') and content_str.endswith('}'):
                return json.loads(content_str)
            else:
                # Try to extract JSON from the response
                start_idx = content_str.find('{')
                end_idx = content_str.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    json_str = content_str[start_idx:end_idx]
                    return json.loads(json_str)
                else:
                    # Debug: save response to file for inspection
                    with open('debug_response.txt', 'w', encoding='utf-8') as f:
                        f.write(f"Full response:\n{result}\n\nExtracted content:\n{content_str}")
                    raise RuntimeError(f"Could not find valid JSON in response. Debug info saved to debug_response.txt")

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error calling LLM API: {e}")
        except (json.JSONDecodeError, KeyError) as e:
            # Debug: save response to file for inspection
            try:
                with open('debug_response.txt', 'w', encoding='utf-8') as f:
                    f.write(f"Full response:\n{result}\n\nExtracted content:\n{content_str}\n\nError: {e}")
            except:
                pass
            raise RuntimeError(f"Error parsing LLM response: {e}\nResponse content saved to debug_response.txt")

    async def _calculate_story_points(self, platform_analyses: Dict[str, PlatformAnalysis],
                                   platform_detection: PlatformDetection) -> Dict[str, int]:
        """Calculate story points for each platform and overall"""

        platform_story_points = {}
        total_score = 0

        for platform, analysis in platform_analyses.items():
            if analysis.factors:
                # Calculate platform score from factors
                platform_score = sum(analysis.factors.values())

                # Map to story points using configurable mapping
                platform_sp = self._map_score_to_story_points(platform_score)
                platform_story_points[platform] = platform_sp
                total_score += platform_score

        # Calculate overall story points (weighted average)
        if platform_story_points:
            overall_sp = self._map_score_to_story_points(total_score // len(platform_story_points))
        else:
            overall_sp = 3  # Default

        return {
            "by_platform": platform_story_points,
            "overall": overall_sp
        }

    def _map_score_to_story_points(self, score: int) -> int:
        """Map complexity score to Fibonacci story points"""

        mapping = self.config_data.get("platform_mapping", {})

        if score <= mapping.get("sp1_max", 5):
            return 1
        elif score <= mapping.get("sp2_max", 8):
            return 2
        elif score <= mapping.get("sp3_max", 12):
            return 3
        elif score <= mapping.get("sp5_max", 16):
            return 5
        elif score <= mapping.get("sp8_max", 20):
            return 8
        else:
            return 13

    