import typer
from pathlib import Path
from typing import List, Optional

from story_size.config import load_config
from story_size.config import load_config
from story_size.core.docs import read_documents
from story_size.core.code_analysis import analyze_code
from story_size.core.ai_client import score_factors
from story_size.core.scoring import calculate_complexity_score, map_to_story_points, get_confidence
from story_size.core.models import Estimation, CodeSummary, AuditFootnote

app = typer.Typer()

@app.command()
def main(
    docs_dir: Path = typer.Option(..., "--docs-dir", help="Directory containing the work item's documents."),
    code_dir: Path = typer.Option(..., "--code-dir", help="Directory containing the relevant codebase."),
    paths: Optional[str] = typer.Option(None, "--paths", help="Comma-separated subpaths inside code-dir to prioritise."),
    languages: Optional[str] = typer.Option(None, "--languages", help="Subset of: csharp,typescript,javascript,dart."),
    output: str = typer.Option("text", "--output", help="Output mode (json|text)."),
    scope: str = typer.Option("project:default/org:default", "--scope", help="Used for audit_footnote.scope."),
    config: Optional[Path] = typer.Option(None, "--config", help="Config file for model endpoint, weights, mapping ranges, etc."),
):
    """
    Estimates the story points for a given work item.
    """
    if not docs_dir.is_dir():
        print(f"Error: --docs-dir '{docs_dir}' is not a directory.")
        raise typer.Exit(code=1)

    if not code_dir.is_dir():
        print(f"Error: --code-dir '{code_dir}' is not a directory.")
        raise typer.Exit(code=1)

    doc_text = read_documents(docs_dir)
    
    config_data = load_config(config)

    parsed_paths = paths.split(',') if paths else None
    parsed_languages = languages.split(',') if languages else None

    code_analysis_summary = analyze_code(code_dir, paths=parsed_paths, languages=parsed_languages)

    factors = score_factors(doc_text, code_analysis_summary, {}, config_data)

    complexity_score = calculate_complexity_score(factors, config_data.get("weights", {}))
    story_points = map_to_story_points(complexity_score, config_data.get("mapping", {}))
    confidence = get_confidence(factors)

    code_summary = CodeSummary(
        files_estimated=sum(code_analysis_summary["files_by_language"].values()),
        services_touched=[], # Placeholder
        db_migrations_estimated=0, # Placeholder
        languages_seen=code_analysis_summary["languages_seen"]
    )

    audit_footnote = AuditFootnote(
        scope=scope,
        memory_ops=[],
        logs_touched=[],
        websearch=False,
        gating="passed"
    )

    estimation = Estimation(
        story_points=story_points,
        scale=[1, 2, 3, 5, 8, 13],
        complexity_score=complexity_score,
        factors=factors,
        confidence=confidence,
        rationale=[], # Placeholder
        code_summary=code_summary,
        audit_footnote=audit_footnote
    )

    if output == "json":
        print(estimation.model_dump_json(indent=2))
    else:
        print(f"Suggested: {estimation.story_points} story points (confidence {estimation.confidence:.2f}), complexity_score={estimation.complexity_score}")
        print(f"Factors: DC={estimation.factors.dc}, IC={estimation.factors.ic}, IB={estimation.factors.ib}, DS={estimation.factors.ds}, NR={estimation.factors.nr}")
        print("\nRationale:")
        for line in estimation.rationale:
            print(f"- {line}")
        print("\nAuditFootnote:")
        print(estimation.audit_footnote.model_dump_json())



if __name__ == "__main__":
    app()
