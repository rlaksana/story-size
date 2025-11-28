# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered Story Size Estimator - a Python CLI tool that analyzes documentation and codebases to estimate story points for work items using LLM-powered scoring of effort factors.

## Common Commands

### Development Setup
```bash
# Activate virtual environment
source venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt

# Run the tool
python main.py --docs-dir <path> --code-dir <path>
```

### Building
```bash
# Build executable
pyinstaller --onefile main.py --name story-size
# Output: dist/story-size.exe
```

### Running the Tool
```bash
# Basic usage
story-size --docs-dir docs/ --code-dir src/

# With options
story-size --docs-dir docs/ --code-dir src/ \
  --paths "api,billing" \
  --languages "csharp,typescript" \
  --output json \
  --scope "project:billing/org:acme" \
  --config custom.yml
```

## Architecture

### Core Processing Pipeline
1. **Document Processing** (`story_size/core/docs.py`) - Multi-format document reader supporting PDF, DOCX, XLSX, Markdown, and text files
2. **Code Analysis** (`story_size/core/code_analysis.py`) - Analyzes C#, TypeScript, JavaScript, and Dart codebases for file counts, LOC, and complexity metrics
3. **AI Scoring** (`story_size/core/ai_client.py`) - LLM client that scores 5 effort factors (DC, IC, IB, DS, NR) on 1-5 scale
4. **Scoring Logic** (`story_size/core/scoring.py`) - Calculates weighted complexity score and maps to Fibonacci story points
5. **CLI Interface** (`story_size/cli.py`) - Typer-based command-line interface

### Effort Factor Model
The tool scores 5 key factors that drive story point estimation:
- **DC** (Domain Complexity) - Business domain complexity
- **IC** (Implementation Complexity) - Technical implementation difficulty
- **IB** (Integration Breadth) - Number of affected systems/components
- **DS** (Data/Schema Impact) - Data model changes required
- **NR** (Non-Functional & Risk) - Non-functional requirements and risks

### Data Models (`story_size/core/models.py`)
Strong type safety using Pydantic models:
- `Factors` - Effort factor scores (1-5 scale for each factor)
- `CodeSummary` - Analysis results (files_estimated, services_touched, languages_seen)
- `AuditFootnote` - Audit trail metadata for tracking
- `Estimation` - Complete result with confidence scoring and rationale

### Configuration System (`story_size/config.py`)
YAML-based configuration with deep merge support:
- **LLM Settings**: Endpoint, API key environment variable, model selection
- **Weights**: Customizable weights for each effort factor (default: 1.0 each)
- **Mapping**: Fibonacci story point ranges (sp1_max through sp13_max)
- **Override**: Custom config files can override defaults selectively

Default LLM endpoint: ZAI API (Anthropic-compatible) using glm-4.6 model.

### Key Technical Details

#### Scoring Algorithm
```python
complexity_score = Σ(factor_score × weight)
story_points = map_complexity_to_fibonacci(score)
```

#### Document Support
- Text: `.md`, `.txt`
- Office: `.pdf`, `.docx`, `.xlsx`
- Libraries: `pypdf`, `python-docx`, `openpyxl`

#### Code Analysis Features
- Languages: C#, TypeScript/JavaScript, Dart
- Metrics: File count, lines of code, large file detection (>500 lines)
- Path filtering and language filtering support

#### Error Handling
- Graceful document parsing failures (skips unreadable files)
- Network timeout handling for LLM API calls
- JSON response parsing with fallback for code-block wrapped responses
- Input validation for directory paths and file formats

## Development Notes

### Environment Variables
- `ZAI_API_KEY` - Required for LLM API access (or customize via config)

### CLI Output Formats
- **text**: Human-readable summary with factors and confidence
- **json**: Full structured output with all estimation details

### Path Filtering
Use `--paths` to prioritize specific subdirectories within the codebase for more focused analysis.

### Language Support
Current languages: `csharp`, `typescript`, `javascript`, `dart`. Extend support in `code_analysis.py`.