# Story Point Estimation Logic: Analysis & Critique

This document explains how the **Story Size Estimator** calculates story points, critiques the current approach, and proposes enhancements.

## 1. Current Mechanism

### The Core Concept
The tool uses a **Factor-Based Estimation** model. The AI scores specific **complexity factors**, which are then mathematically combined to produce a story point estimate.

### The 5 Effort Factors
The AI scores the following on a scale of **1 to 5**:

| Factor | Name | Description |
| :--- | :--- | :--- |
| **DC** | **Domain Complexity** | Difficulty of business logic. |
| **IC** | **Implementation Complexity** | Technical difficulty (legacy code, algorithms). |
| **IB** | **Integration Breadth** | Number of affected systems. |
| **DS** | **Data / Schema Impact** | Changes to data models. |
| **NR** | **Non-Functional & Risk** | Security, performance, compliance. |

### The Scoring Algorithm
```python
Complexity Score = (DC * Weight) + (IC * Weight) + (IB * Weight) + (DS * Weight) + (NR * Weight)
```
*   **Default**: Weights are 1.0.
*   **Mapping**: The sum is mapped to Fibonacci numbers (e.g., score 1-7 = 1 SP, 17-20 = 8 SP).

---

## 2. Critique of Current Logic

While the current model is a good starting point, it has several **theoretical and practical flaws**:

### A. Linearity Assumption (Major Flaw)
The formula assumes complexity is **additive**.
*   *Reality*: Complexity is often **multiplicative** or exponential. A task with high Domain Complexity AND high Integration Breadth is usually *much* harder than the sum of its parts.
*   *Issue*: A story with `DC=5, IC=5` (Score 10) might be mapped to **2 SP**, which is likely a gross underestimation for a task that is both complex to understand and hard to build.

### B. Subjective Scaling
The "1-5" scale is arbitrary for an LLM without calibration.
*   *Issue*: What is a "3" for `glm-4.6`? Without reference examples (few-shot prompting), the model might drift. A "3" today might be a "5" tomorrow.

### C. Arbitrary Thresholds
The mapping (e.g., "17-20 score = 8 points") is hardcoded.
*   *Issue*: Every team has a different "velocity" and definition of a point. These hardcoded ranges will likely fail for teams that size differently (e.g., teams where an "8" is a month of work vs. teams where an "8" is a week).

### D. Lack of Historical Context
The tool treats every estimation in a vacuum.
*   *Issue*: It doesn't learn from past mistakes. If the tool consistently underestimates "Billing" tasks, it has no feedback loop to correct itself.

---

## 3. Proposed Enhancements

To make this tool "Production Grade", I recommend the following improvements:

### Enhancement 1: Non-Linear Scoring Formula
Switch to a formula that penalizes high complexity more aggressively.
*   **New Formula**: `Score = (DC^1.5) + (IC^1.5) + ...`
*   **Why**: This ensures that high scores in critical areas push the estimate up significantly, better reflecting the risk of "unknown unknowns".

### Enhancement 2: Few-Shot Calibration (Context Injection)
Allow the user to provide 3-5 examples of *past* stories and their actual points in the `config.yml`.
*   **Implementation**: Inject these into the system prompt: *"Here is an example of a 3-point story: [Summary]. Here is an 8-point story: [Summary]. Compare the current task to these."*
*   **Benefit**: Anchors the LLM to the team's specific reality.

### Enhancement 3: Confidence Intervals
Instead of a single number, output a **Range**.
*   **Implementation**: If the factors have high variance (e.g., DC=1 but NR=5), the uncertainty is high.
*   **Output**: "Estimated: 5 SP (Range: 3 - 8 SP)".
*   **Benefit**: Honest communication of risk.

### Enhancement 4: "Risk Multiplier" Factor
Add a specific check for "Codebase Health" in the target directory.
*   **Implementation**: If `code_analysis.py` detects high cyclomatic complexity or low test coverage in the target files, apply a **1.2x - 1.5x multiplier** to the final score.
*   **Benefit**: Accounts for the "Legacy Code Tax" that pure requirement analysis misses.
