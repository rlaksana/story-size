from pathlib import Path
from typing import Dict, List, Optional

SUPPORTED_LANGUAGES = {
    "csharp": [".cs"],
    "typescript": [".ts", ".tsx"],
    "javascript": [".js", ".jsx"],
    "dart": [".dart"],
}

def analyze_code(
    code_dir: Path,
    paths: Optional[List[str]] = None,
    languages: Optional[List[str]] = None,
) -> Dict:
    """
    Analyzes the code in the given directory and returns a summary.
    """
    if languages is None:
        languages = list(SUPPORTED_LANGUAGES.keys())

    files_by_language = {lang: 0 for lang in languages}
    loc_by_language = {lang: 0 for lang in languages}
    large_files_by_language = {lang: 0 for lang in languages}
    
    search_paths = [code_dir]
    if paths:
        search_paths = [code_dir / p for p in paths]

    for search_path in search_paths:
        for lang in languages:
            extensions = SUPPORTED_LANGUAGES[lang]
            for ext in extensions:
                for file_path in search_path.rglob(f"*{ext}"):
                    files_by_language[lang] += 1
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                            loc = len(lines)
                            loc_by_language[lang] += loc
                            if loc > 500:
                                large_files_by_language[lang] += 1
                    except Exception:
                        # Ignore files that can't be read
                        pass

    return {
        "languages_seen": [lang for lang, count in files_by_language.items() if count > 0],
        "files_by_language": files_by_language,
        "loc_by_language": loc_by_language,
        "large_files_by_language": large_files_by_language,
    }
