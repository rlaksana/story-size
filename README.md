# AI Story Size Estimator

A Python CLI tool that analyzes documentation and codebases to estimate story points for work items using AI-powered platform-aware analysis.

## Features

- **Platform-Aware Analysis**: Separate analysis for frontend, backend, mobile, and devops platforms
- **Multi-Format Document Support**: PDF, DOCX, XLSX, Markdown, and text files with OCR for images
- **Code Analysis**: Supports C#, TypeScript, JavaScript, and Dart codebases
- **Extended Fibonacci Scale**: 1, 2, 3, 5, 8, 13, 21, 34, 55 for enterprise projects
- **Detailed Calculation Breakdown**: See raw scores, impact taxes, and multipliers
- **Hours Estimation**: Non-linear models (exponential, power, linear) for time estimates
- **Auto-Save Reports**: Generate markdown reports automatically

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd story-size
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   # Copy .env.example to .env
   cp .env.example .env

   # Edit .env and add your API key
   # ZAI_API_KEY=your_api_key_here
   ```

## Quick Start

### Basic Usage

```bash
python main.py main --docs-dir <path_to_docs> --output-md <output_file.md> --output enhanced
```

### With Platform Auto-Detection

```bash
python main.py main --docs-dir specs/ --code-dir ../repo --output-md report.md --output enhanced --auto-save
```

### With Manual Platform Directories

```bash
python main.py main \
  --docs-dir specs/ \
  --fe-dir ../frontend \
  --be-dir ../backend \
  --mobile-dir ../mobile \
  --output-md report.md \
  --output enhanced
```

## Command-Line Options

### Document Input
| Flag | Description |
|------|-------------|
| `--docs-dir <path>` | Directory containing work item documents (required) |

### Code Directories
| Flag | Description | Env Var |
|------|-------------|---------|
| `--code-dir <path>` | Code directory for auto-detection | `DEFAULT_REPO_PATH` |
| `--fe-dir <path>` | Frontend code directory | `DEFAULT_FE_DIR` |
| `--be-dir <path>` | Backend code directory | `DEFAULT_BE_DIR` |
| `--mobile-dir <path>` | Mobile code directory | `DEFAULT_MOBILE_DIR` |
| `--devops-dir <path>` | DevOps code directory | `DEFAULT_DEVOPS_DIR` |
| `--auto-detect-dirs` | Auto-detect platform directories from code-dir | |

### Analysis Options
| Flag | Description |
|------|-------------|
| `--force-platforms <list>` | Force analysis for specific platforms: frontend,backend,mobile,devops |
| `--paths <paths>` | Comma-separated subpaths to prioritize |
| `--languages <list>` | Subset: csharp, typescript, javascript, dart |

### Output Options
| Flag | Description | Env Var |
|------|-------------|---------|
| `--output <format>` | Output format: `enhanced` (default), `text`, `json` | |
| `--output-md <path>` | Save markdown report to file | |
| `--output-dir <path>` | Default directory for markdown reports | `DEFAULT_OUTPUT_DIR` |
| `--auto-save` | Auto-save to output-dir with generated filename | `DEFAULT_AUTO_SAVE` |
| `--show-all-estimates` | Show all hours estimation models | |

### Configuration
| Flag | Description |
|------|-------------|
| `--config <path>` | Path to custom config.yml file |

## Environment Variables

Create a `.env` file from `.env.example`:

```bash
# Required
ZAI_API_KEY=your_api_key_here

# Optional defaults
DEFAULT_BACKLOG_PATH=D:\path\to\specs
DEFAULT_REPO_PATH=D:\path\to\repository
DEFAULT_OUTPUT_DIR=D:\path\to\output
DEFAULT_AUTO_SAVE=false
```

## Output Formats

### Enhanced Output (Default)

Detailed platform-aware analysis with:
- Platform breakdown (Frontend, Backend, Mobile, DevOps)
- Raw scores, impact taxes, adjusted scores
- Story points per platform and overall
- Estimated hours range
- Detailed explanations and recommended approaches

### Markdown Report

```bash
python main.py main --docs-dir specs/ --output-md report.md --output enhanced
```

Generates a detailed markdown report with:
- Summary table with key metrics
- Platform breakdown table with calculation details
- Overall calculation formula breakdown
- Detailed analysis per platform
- Platform requirements and technologies

## PowerShell Scripts

For Windows automation, use the provided PowerShell scripts:

### run-story-size-python.ps1

```powershell
.\run-story-size-python.ps1
```

Runs the tool directly with Python. Edit the script to customize:
- Input/output directories
- CLI options
- Platform directories

## Fibonacci Scale

The tool uses an extended Fibonacci sequence for enterprise projects:

| Story Points | Complexity | Typical Hours |
|--------------|------------|---------------|
| 1 | Trivial | 3-5h |
| 2 | Simple | 5-8h |
| 3 | Moderate | 8-13h |
| 5 | Average | 13-21h |
| 8 | Complex | 21-34h |
| 13 | Very Complex | 34-55h |
| 21 | Multi-platform | 55-89h |
| 34 | Large-scale | 89-144h |
| 55 | Enterprise | 144+ hours |

## Calculation Logic

**Overall Story Points Formula:**

```
final_score = (sum(platform_raw_scores) × integration_multiplier) × risk_multiplier
story_points = map_to_fibonacci(final_score)
```

**Where:**
- `platform_raw_scores` = AI-assessed complexity per platform (1-25 scale)
- `integration_multiplier` = Based on platform count, legacy status, traffic volume
- `risk_multiplier` = Based on uncertainty factors (1.0 - 2.0)

**Platform Story Points Formula:**

```
platform_score = raw_score × impact_tax
platform_sp = map_to_fibonacci(platform_score)
```

**Where `impact_tax` is:**
- 1.0x for LOCAL impact (single file/component)
- 1.2x for MODULE impact (multiple files in module)
- 1.5x for SYSTEM impact (cross-module changes)
- 2.0x for CRITICAL impact (core system changes)

## Building the Executable

```bash
pyinstaller --onefile main.py --name story-size
```

Output: `dist/story-size.exe`

## Configuration

Create a `config.yml` to customize:

```yaml
llm:
  endpoint: https://api.z.ai/api/anthropic/v1/messages
  api_key_env: ZAI_API_KEY
  model: glm-4.6

platform_mapping:
  sp1_max: 5
  sp2_max: 8
  sp3_max: 12
  sp5_max: 16
  sp8_max: 20
  sp13_max: 25
  sp21_max: 35
  sp34_max: 50

hours_estimation:
  base_hours_per_point: 4.0
  uncertainty_factor_min: 0.6
  uncertainty_factor_max: 1.8
```

## Project Structure

```
story-size/
├── main.py                 # CLI entry point
├── .env.example            # Environment variables template
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── story_size/
│   ├── cli.py             # Typer CLI interface
│   ├── core/
│   │   ├── docs_enhanced.py       # Document processing
│   │   ├── code_analysis.py        # Codebase analysis
│   │   ├── platform_ai_client.py   # AI-powered analysis
│   │   ├── hours_estimation.py     # Hours estimation models
│   │   ├── directory_resolver.py   # Platform directory detection
│   │   └── models.py               # Pydantic data models
│   └── config.py          # Configuration defaults
├── planning/               # Planning documents
└── run-story-size-python.ps1  # PowerShell script
```

## Troubleshooting

### Unicode Encoding Error on Windows

If you see encoding errors, the tool automatically configures UTF-8 for Windows terminals. If issues persist:

```powershell
# Set UTF-8 encoding in PowerShell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
```

### Performance Issues

For large codebases, the tool automatically:
- Disables impact analysis after 30 seconds
- Limits project tree depth to 99 directories
- Truncates large file trees in prompts

### Context Window Exceeded

If the LLM context is exceeded:
- Reduce `max_prompt_length` in config (default: 500000)
- Use `--paths` to focus on specific directories
- Use `--force-platforms` to analyze fewer platforms

## License

MIT
