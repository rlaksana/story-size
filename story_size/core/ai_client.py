import os
import json
import requests
from typing import Dict, Tuple
from story_size.core.models import Factors, ScoreExplanations

def score_factors(doc_summary: str, code_summary: dict, metrics: dict, config_data: dict) -> Tuple[Factors, ScoreExplanations]:
    """
    Scores the effort factors based on the document summary, code summary, and metrics.
    Returns both the factors and their explanations.
    """
    llm_config = config_data.get("llm", {})
    endpoint = llm_config.get("endpoint")
    api_key_env = llm_config.get("api_key_env")
    model = llm_config.get("model")

    api_key = os.environ.get(api_key_env)

    if not api_key:
        raise ValueError(f"API key not found in environment variable: {api_key_env}")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "anthropic-version": "2023-06-01",
    }

    system_prompt = """Analyze the following work item and codebase summary to estimate the effort required.
    Provide a score from 1 to 5 for each of the five effort factors WITH detailed explanations:
    - DC (Domain Complexity): How complex is the business domain?
    - IC (Implementation Complexity): How complex is the technical implementation?
    - IB (Integration Breadth): How many other systems or components are affected?
    - DS (Data / Schema Impact): How much does this change affect the data model?
    - NR (Non-Functional & Risk): What are the non-functional requirements and risks?

    Return a JSON object with scores AND explanations, like this:
    {"DC": 3, "IC": 2, "IB": 4, "DS": 2, "NR": 5,
    "explanations": {
        "DC": "Detailed explanation why this DC score was given based on domain complexity",
        "IC": "Detailed explanation why this IC score was given based on implementation complexity",
        "IB": "Detailed explanation why this IB score was given based on integration breadth",
        "DS": "Detailed explanation why this DS score was given based on data/schema impact",
        "NR": "Detailed explanation why this NR score was given based on non-functional requirements and risks"
    }}
    """
    
    user_prompt = f"""Work Item Document Summary:
    ---
    {doc_summary}
    ---

    Codebase Summary:
    ---
    {json.dumps(code_summary, indent=2)}
    ---
    """

    data = {
        "model": model,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.2,
    }

    try:
        response = requests.post(endpoint, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()

        content_str = result['content'][0]['text']
        # The response from Anthropic is often wrapped in a code block
        if "```json" in content_str:
            content_str = content_str.split("```json")[1].split("```")[0]
        
        factor_data = json.loads(content_str)

        # Extract scores
        scores = {k: v for k, v in factor_data.items() if k in ["DC", "IC", "IB", "DS", "NR"]}

        # Extract explanations
        explanations = factor_data.get("explanations", {})
        score_explanations = ScoreExplanations(
            dc_explanation=explanations.get("DC", "No explanation provided for DC score"),
            ic_explanation=explanations.get("IC", "No explanation provided for IC score"),
            ib_explanation=explanations.get("IB", "No explanation provided for IB score"),
            ds_explanation=explanations.get("DS", "No explanation provided for DS score"),
            nr_explanation=explanations.get("NR", "No explanation provided for NR score")
        )

        return Factors(**scores), score_explanations

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Error calling LLM API: {e}")
    except (json.JSONDecodeError, KeyError) as e:
        raise RuntimeError(f"Error parsing LLM response: {e}")
