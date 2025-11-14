import os
import json
import requests
from typing import Dict
from story_size.core.models import Factors

def score_factors(doc_summary: str, code_summary: dict, metrics: dict, config_data: dict) -> Factors:
    """
    Scores the effort factors based on the document summary, code summary, and metrics.
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
    Provide a score from 1 to 5 for each of the five effort factors:
    - DC (Domain Complexity): How complex is the business domain?
    - IC (Implementation Complexity): How complex is the technical implementation?
    - IB (Integration Breadth): How many other systems or components are affected?
    - DS (Data / Schema Impact): How much does this change affect the data model?
    - NR (Non-Functional & Risk): What are the non-functional requirements and risks?

    Return a JSON object with the scores, like this:
    {"DC": 1, "IC": 2, "IB": 3, "DS": 4, "NR": 5, "notes": ["Note 1", "Note 2"]}
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

        return Factors(**factor_data)

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Error calling LLM API: {e}")
    except (json.JSONDecodeError, KeyError) as e:
        raise RuntimeError(f"Error parsing LLM response: {e}")
