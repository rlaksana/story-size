from pathlib import Path
from typing import Optional, Dict, List
from story_size.core.models import PlatformDirectories

class DirectoryResolver:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir

    def resolve_platform_directories(
        self,
        fe_dir: Optional[Path] = None,
        be_dir: Optional[Path] = None,
        mobile_dir: Optional[Path] = None,
        devops_dir: Optional[Path] = None,
        code_dir: Optional[Path] = None,
        auto_detect: bool = False
    ) -> PlatformDirectories:
        """Resolve and validate platform directories"""

        if auto_detect and code_dir:
            return self.auto_detect_platforms(code_dir)

        # Use explicit platform directories
        platform_dirs = PlatformDirectories(
            fe_dir=self._validate_directory(fe_dir, "frontend"),
            be_dir=self._validate_directory(be_dir, "backend"),
            mobile_dir=self._validate_directory(mobile_dir, "mobile"),
            devops_dir=self._validate_directory(devops_dir, "devops"),
            unified_dir=self._validate_directory(code_dir, "unified")
        )

        return platform_dirs

    def _validate_directory(self, directory: Optional[Path], platform: str) -> Optional[Path]:
        """Validate and return directory if it exists"""
        if directory is None:
            return None

        if not directory.exists():
            print(f"Warning: {platform} directory '{directory}' does not exist")
            return None

        if not directory.is_dir():
            print(f"Warning: {platform} path '{directory}' is not a directory")
            return None

        return directory

    def auto_detect_platforms(self, base_dir: Path) -> PlatformDirectories:
        """Auto-detect platform directories from base directory"""

        detection_patterns = {
            "frontend": [
                "frontend", "fe", "web", "client", "ui", "src/app", "src/components",
                "src/views", "src/pages", "public", "assets"
            ],
            "backend": [
                "backend", "be", "server", "api", "src/api", "src/services",
                "src/controllers", "src/models", "src/business"
            ],
            "mobile": [
                "mobile", "app", "ios", "android", "flutter", "react-native",
                "src/mobile", "lib"  # Flutter lib directory
            ],
            "devops": [
                "devops", "infra", "deployment", "docker", "k8s", "kubernetes",
                ".github", "ci-cd", "pipeline", "terraform"
            ]
        }

        detected_dirs = {"unified_dir": base_dir}

        platform_field_mapping = {
            "frontend": "fe_dir",
            "backend": "be_dir",
            "mobile": "mobile_dir",
            "devops": "devops_dir"
        }

        for platform, patterns in detection_patterns.items():
            for pattern in patterns:
                candidate_dir = base_dir / pattern
                if candidate_dir.exists() and self.is_platform_directory(candidate_dir, platform):
                    detected_dirs[platform_field_mapping[platform]] = candidate_dir
                    print(f"Auto-detected {platform} directory: {candidate_dir}")
                    break

        return PlatformDirectories(**detected_dirs)

    def is_platform_directory(self, directory: Path, platform: str) -> bool:
        """Verify if directory actually contains platform-specific files"""

        platform_files = {
            "frontend": [".tsx", ".ts", ".jsx", ".js", ".vue", ".svelte", ".html", ".css", ".scss"],
            "backend": [".cs", ".py", ".java", ".go", ".php", ".rb", ".sql"],
            "mobile": [".dart", ".kt", ".swift", ".java", ".xml"],
            "devops": [".yml", ".yaml", "dockerfile", "tf", ".json", "bicep", ".sh", ".ps1"]
        }

        expected_files = platform_files.get(platform, [])
        file_count = 0

        # Check if directory contains expected file types
        for file_path in directory.rglob("*"):
            if file_path.is_file() and file_path.suffix in expected_files:
                file_count += 1
                if file_count >= 3:  # Require at least 3 relevant files
                    return True

        return False

    def get_platform_languages(self, platform: str, user_languages: Optional[List[str]] = None) -> List[str]:
        """Get priority languages for a platform"""

        platform_defaults = {
            "frontend": ["typescript", "javascript"],
            "backend": ["csharp", "python", "java", "go"],
            "mobile": ["dart", "kotlin", "swift"],
            "devops": ["yaml", "json"]
        }

        if user_languages:
            # Filter user languages by platform relevance
            platform_langs = platform_defaults.get(platform, [])
            return [lang for lang in user_languages if lang in platform_langs] or platform_langs

        return platform_defaults.get(platform, [])

    def identify_key_files(self, platform_dir: Path, platform: str) -> List[str]:
        """Identify key files for platform-specific analysis"""

        key_patterns = {
            "frontend": [
                "package.json", "tsconfig.json", "webpack.config.js", "vite.config.js",
                "App.tsx", "index.tsx", "main.tsx", "router.tsx"
            ],
            "backend": [
                "appsettings.json", "Program.cs", "Startup.cs", "app.js", "server.js",
                "requirements.txt", "Dockerfile", "docker-compose.yml"
            ],
            "mobile": [
                "pubspec.yaml", "android/app/build.gradle", "ios/Runner.xcodeproj",
                "lib/main.dart", "AppDelegate.swift", "MainActivity.kt"
            ],
            "devops": [
                "Dockerfile", "docker-compose.yml", "k8s/", ".github/workflows/",
                "terraform/", "azure-pipelines.yml", "Jenkinsfile"
            ]
        }

        key_files = []
        patterns = key_patterns.get(platform, [])

        for pattern in patterns:
            if pattern.endswith("/"):
                # Directory pattern
                pattern_dir = platform_dir / pattern
                if pattern_dir.exists():
                    for file_path in pattern_dir.rglob("*"):
                        if file_path.is_file():
                            rel_path = str(file_path.relative_to(platform_dir))
                            key_files.append(rel_path)
                            if len(key_files) >= 10:  # Limit results
                                break
            else:
                # File pattern
                candidate = platform_dir / pattern
                if candidate.exists():
                    key_files.append(pattern)
                    if len(key_files) >= 10:
                        break

        return key_files[:10]  # Limit to top 10 key files