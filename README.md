# AI Story Size Estimator

A local Python CLI tool that analyzes documentation and a codebase to estimate story points for a work item.

## How to Use

1.  **Provide a real API Key**: Set the `ZAI_API_KEY` environment variable to your API key.
2.  **Run from the command line**:

    ```bash
    story-size.exe --docs-dir <path_to_docs> --code-dir <path_to_code>
    ```

    -   `--docs-dir`: Path to the directory containing the work item's documents (`.md`, `.txt`, `.pdf`, `.docx`, `.xlsx`).
    -   `--code-dir`: Path to the directory containing the relevant codebase.

### Optional Flags

-   `--paths <relative_paths>`: Comma-separated subpaths inside `code-dir` to prioritise.
-   `--languages <list>`: Subset of: `csharp`, `typescript`, `javascript`, `dart`.
-   `--output json|text`: Output mode (default: `text`).
-   `--config <path>`: Path to a `config.yml` file to override default settings.

## Building the Executable

To build the `story-size.exe` executable, you need to have Python and PyInstaller installed.

1.  **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

2.  **Build the executable**:

    ```bash
    pyinstaller --onefile main.py --name story-size
    ```

    The executable will be located in the `dist` directory.