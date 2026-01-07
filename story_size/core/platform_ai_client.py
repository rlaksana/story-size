import os
import json
import requests
import warnings  # NEW: Suppress warnings from other libraries
from typing import Dict, Optional, List
from pathlib import Path

# Suppress warnings from imported packages (e.g., PyTorch, TensorFlow, etc.)
warnings.filterwarnings("ignore", category=UserWarning)

from story_size.core.models import (
    PlatformDetection, PlatformAnalysis, CompleteAnalysis,
    PlatformRequirement, EnhancedCodeAnalysis
)
from story_size.core.platform_detector import PlatformDetector
from story_size.core.context_detector import (
    auto_detect_context,
    RiskKeywordDetector,
    LegacyStatusDetector,
    TrafficVolumeDetector
)
from story_size.core.impact_analyzer import (
    ImpactAnalyzer,
    ImpactScope,
    analyze_all_platforms_impact
)

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
                                  image_analysis: dict = None,
                                  code_dir: Path = None) -> CompleteAnalysis:
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

            # Stage 1.5: Impact Analysis (DISABLED - too slow for large codebases)
            # TODO: Re-enable after optimizing for performance (async file scanning, caching, etc.)
            # print("Stage 1.5: Analyzing impact scope...")
            # impact_scopes = analyze_all_platforms_impact(doc_summary, code_analysis)
            # for platform, impact in impact_scopes.items():
            #     print(f"  {platform.upper()}: {impact.total_affected_files} files affected ({impact.impact_ratio:.1%})")
            impact_scopes = None  # Pass None to _calculate_story_points

            # Auto-detect context for transparency (DISABLED - too slow for large codebases)
            # TODO: Re-enable after optimizing for performance (async file scanning, caching, etc.)
            # if code_dir:
            #     context_summary = self.get_context_summary(code_dir, doc_summary)
            #     if context_summary:
            #         print(f"[Auto-detected Context]")
            #         if context_summary.get("legacy_status"):
            #             print(f"  Legacy Status: {context_summary['legacy_status']}")
            #         if context_summary.get("traffic_volume"):
            #             print(f"  Traffic Volume: {context_summary['traffic_volume']}")
            #         if context_summary.get("risk_multiplier", 1.0) > 1.0:
            #             print(f"  Risk Multiplier: {context_summary['risk_multiplier']}")

            # Stage 2: Analyze each required platform
            platform_analyses = {}
            for platform in platform_detection.estimated_platforms:
                print(f"Stage 2: Analyzing {platform}...")
                platform_analyses[platform] = await self.analyze_platform(
                    platform, doc_summary, code_analysis, platform_detection, image_analysis
                )
                print(f"{platform} analysis complete")

            # Calculate story points with enhanced formula (impact x integration x risk)
            story_points_data = await self._calculate_story_points(
                platform_analyses,
                platform_detection,
                code_analysis,
                code_dir,
                doc_summary,
                impact_scopes  # NEW: Pass impact scopes
            )

            return CompleteAnalysis(
                platform_detection=platform_detection,
                platform_analyses=platform_analyses,
                overall_story_points=story_points_data["overall"],
                platform_story_points=story_points_data["by_platform"],
                confidence_score=platform_detection.confidence,
                calculation_breakdown=story_points_data.get("calculation_breakdown")  # NEW: Pass calculation details
            )

        except Exception as e:
            import traceback
            print(f"Platform-aware analysis failed: {e}")
            print("\n[FULL TRACEBACK]")
            traceback.print_exc()
            print("\n[END TRACEBACK]\n")
            # Re-raise the exception since traditional fallback is removed
            raise Exception(f"Platform-aware analysis failed and no fallback available: {e}")

    def _generate_platform_structure_analysis(self, code_analysis: EnhancedCodeAnalysis,
                                          include_tree: bool = False, max_tree_lines: int = 50) -> str:
        """Generate structured analysis of available platform code with optional project tree"""

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

                    # Add project tree for better AI context (ONLY when explicitly requested)
                    # For platform detection, skip the tree to avoid context overflow
                    if include_tree and summary.project_tree:
                        structure_lines.append(f"  - Project Structure (truncated to {max_tree_lines} lines):")
                        tree_lines = summary.project_tree.split("\n")
                        for tree_line in tree_lines[:max_tree_lines]:
                            structure_lines.append(f"    {tree_line}")
                        if len(tree_lines) > max_tree_lines:
                            structure_lines.append(f"    ... ({len(tree_lines) - max_tree_lines} more lines omitted)")

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
                                   platform_detection: PlatformDetection,
                                   code_analysis: EnhancedCodeAnalysis = None,
                                   code_dir: Path = None,
                                   doc_summary: str = "",
                                   impact_scopes: Dict[str, ImpactScope] = None) -> Dict[str, int]:
        """
        Calculate story points using the Enhanced Formula from Gemini discussion:

        1. Calculate base platform scores (AI complexity assessment)
        2. Apply impact tax multiplier (based on affected files ratio)
        3. Apply integration overhead (context switching + glue cost)
        4. Apply risk multiplier (uncertainty buffer)
        5. Map to nearest Fibonacci number

        REVISED Formula: final_score = base_score x impact_tax x integration_multiplier x risk_multiplier

        KEY CHANGE: Impact is a TAX (multiplier), not a FILTER (reducer).
        - Small impact doesn't reduce the score for complex tasks
        - Large impact adds overhead for testing/deployment
        """

        platform_story_points = {}
        platform_scores = {}
        platform_impact_tiers = {}

        # Step 1: Calculate base platform scores (unchanged - this is the AI complexity assessment)
        for platform, analysis in platform_analyses.items():
            if analysis.factors:
                platform_score = sum(analysis.factors.values())
                platform_scores[platform] = platform_score

                # Calculate impact tax multiplier (not a reducer!)
                impact_tax = 1.0  # Default: no extra tax
                impact_tier = "LOCAL (< 1%)"

                if impact_scopes and platform in impact_scopes:
                    impact = impact_scopes[platform]
                    impact_ratio = impact.impact_ratio

                    # Map impact ratio to risk tier (Integration Tax)
                    if impact_ratio < 0.01:
                        # < 1%: Local change, no integration risk
                        impact_tax = 1.0
                        impact_tier = "LOCAL (< 1%)"
                    elif impact_ratio < 0.05:
                        # 1-5%: Module-level, integration testing needed
                        impact_tax = 1.2
                        impact_tier = "MODULE (1-5%)"
                    elif impact_ratio < 0.10:
                        # 5-10%: System-level, regression testing needed
                        impact_tax = 1.5
                        impact_tier = "SYSTEM (5-10%)"
                    else:
                        # > 10%: Architectural change, high danger
                        impact_tax = 2.0
                        impact_tier = "ARCHITECTURAL (> 10%)"

                    platform_impact_tiers[platform] = impact_tier

                    # Print impact info
                    print(f"\n[Impact Analysis: {platform.upper()}]")
                    print(f"  Extracted entities: {', '.join(impact.extracted_entities[:5])}")
                    print(f"  Directly affected files: {len(impact.directly_affected_files)}")
                    print(f"  Cascading changes: {len(impact.cascading_affected_files)}")
                    print(f"  Total affected: {impact.total_affected_files} / {impact.total_files_in_platform} "
                          f"({impact_ratio:.1%})")
                    print(f"  Impact Tier: {impact_tier} -> {impact_tax:.1f}x integration tax")
                    print(f"  Confidence: {impact.confidence:.2f}")
                else:
                    # No impact analysis available, assume full platform impact
                    impact_tax = 1.5
                    impact_tier = "UNKNOWN (assumed SYSTEM)"
                    platform_impact_tiers[platform] = impact_tier

                # Apply impact tax to get adjusted score
                adjusted_score = platform_score * impact_tax
                platform_sp = self._map_score_to_story_points(int(adjusted_score))
                platform_story_points[platform] = platform_sp

        # Auto-detect context from codebase and requirements (with performance safeguards)
        # Use fast mode: limit file scanning to avoid hangs on large codebases
        context_data = {}
        if code_dir and code_dir.exists():
            try:
                # Import here to avoid circular dependency
                import asyncio

                # Run with timeout to prevent hanging
                context_data = await asyncio.wait_for(
                    asyncio.to_thread(auto_detect_context, code_dir, doc_summary),
                    timeout=30.0  # 30 second timeout
                )
            except asyncio.TimeoutError:
                print(f"  [WARN] Context detection timed out (large codebase), using defaults")
            except Exception as e:
                print(f"  [WARN] Context detection failed: {e}, using defaults")

        risk_multiplier = context_data.get("risk_multiplier", 1.0) if context_data else 1.0
        legacy_status = context_data.get("legacy_status", "greenfield") if context_data else "greenfield"
        traffic_volume = context_data.get("traffic_volume", "no_traffic") if context_data else "no_traffic"

        # Step 2: Calculate integration overhead (context switching between platforms)
        platform_count = len(platform_scores)
        integration_multiplier = self._calculate_integration_overhead(
            platform_count,
            legacy_status,
            traffic_volume
        )

        # Step 3: Apply enhanced formula with correct math
        base_sum = sum(platform_scores.values()) if platform_scores else 0

        # Apply multipliers in sequence (not reducing, but adding overhead)
        after_impact_tax = base_sum  # Impact tax already applied per-platform above
        after_integration = after_impact_tax * integration_multiplier
        final_score = after_integration * risk_multiplier

        # Step 4: Map to Fibonacci
        overall_sp = self._map_score_to_story_points(int(final_score))

        # Print calculation information for transparency
        print(f"\n[Enhanced Calculation]")
        print(f"  Platform scores (base -> after impact tax):")
        for platform, base_score in platform_scores.items():
            if platform in platform_impact_tiers:
                tier = platform_impact_tiers[platform]
                tax = 1.0 if "LOCAL" in tier else (1.2 if "MODULE" in tier else (1.5 if "SYSTEM" in tier else 2.0))
                adjusted = base_score * tax
                print(f"    {platform}: {base_score:.2f} -> {adjusted:.2f} ({tier}, {tax:.1f}x)")
        print(f"  Base sum: {base_sum:.2f}")
        print(f"  Integration multiplier: {integration_multiplier:.2f} "
              f"(platforms={platform_count}, legacy={legacy_status}, traffic={traffic_volume})")
        print(f"  Risk multiplier: {risk_multiplier:.2f}")
        print(f"  Final score: {final_score:.2f} -> {overall_sp} story points")

        # Build detailed breakdown for report
        platform_breakdown = {}
        for platform, base_score in platform_scores.items():
            tax = 1.0  # Default
            tier = "UNKNOWN"
            if platform in platform_impact_tiers:
                tier = platform_impact_tiers[platform]
                tax = 1.0 if "LOCAL" in tier else (1.2 if "MODULE" in tier else (1.5 if "SYSTEM" in tier else 2.0))

            adjusted = base_score * tax
            platform_breakdown[platform] = {
                "raw_score": base_score,
                "impact_tax": tax,
                "impact_tier": tier,
                "adjusted_score": adjusted,
                "story_points": platform_story_points.get(platform, 0)
            }

        calculation_breakdown = {
            "platform_breakdown": platform_breakdown,
            "base_sum": base_sum,
            "integration_multiplier": integration_multiplier,
            "risk_multiplier": risk_multiplier,
            "final_score": final_score,
            "overall_story_points": overall_sp,
            "platform_count": platform_count,
            "legacy_status": legacy_status,
            "traffic_volume": traffic_volume
        }

        return {
            "by_platform": platform_story_points,
            "overall": overall_sp,
            "base_sum": base_sum,
            "integration_multiplier": integration_multiplier,
            "risk_multiplier": risk_multiplier,
            "final_score": final_score,
            "platform_impact_tiers": platform_impact_tiers,
            "calculation_breakdown": calculation_breakdown  # NEW: Detailed breakdown
        }

    def _calculate_integration_overhead(self, platform_count: int,
                                       legacy_status: str,
                                       traffic_volume: str) -> float:
        """
        Calculate integration overhead multiplier based on:

        1. Context Switching: Working across multiple platforms
        2. Integration Complexity: Legacy status and traffic volume
        """

        # Base multiplier: 1.0 (no overhead)
        context_switching_multiplier = 1.0
        integration_complexity_multiplier = 1.0

        # Context switching cost (0-50% overhead based on platform count)
        if platform_count >= 4:
            context_switching_multiplier = 1.5
        elif platform_count == 3:
            context_switching_multiplier = 1.3
        elif platform_count == 2:
            context_switching_multiplier = 1.15
        else:
            context_switching_multiplier = 1.0

        # Integration complexity based on legacy status
        legacy_multiplier = {
            "greenfield": 1.0,
            "low_legacy": 1.05,
            "moderate_legacy": 1.15,
            "high_legacy": 1.25,
            "critical_legacy": 1.4
        }.get(legacy_status, 1.0)

        # Integration complexity based on traffic volume
        traffic_multiplier = {
            "no_traffic": 1.0,
            "low_traffic": 1.02,
            "medium_traffic": 1.08,
            "high_traffic": 1.15,
            "critical_traffic": 1.25
        }.get(traffic_volume, 1.0)

        integration_complexity_multiplier = legacy_multiplier * traffic_multiplier

        # Combined multiplier
        return context_switching_multiplier * integration_complexity_multiplier

    def _map_score_to_story_points(self, score: int) -> int:
        """Map complexity score to Fibonacci story points

        Extended Fibonacci sequence for enterprise multi-platform projects:
        0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89...
        """

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
        elif score <= mapping.get("sp13_max", 25):
            return 13
        elif score <= mapping.get("sp21_max", 35):
            return 21
        elif score <= mapping.get("sp34_max", 50):
            return 34
        else:
            return 55  # Cap at 55 for very large enterprise features

    def get_context_summary(self, code_dir: Path, doc_summary: str) -> dict:
        """
        Get detected context summary for transparency/debugging.

        Returns:
            Dictionary with legacy status, traffic volume, tech stack, risk keywords
        """
        if not code_dir or not code_dir.exists():
            return {}

        return auto_detect_context(code_dir, doc_summary)

    