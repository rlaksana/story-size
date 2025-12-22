# Hours Estimation Logic

This document explains the non-linear estimation models used to convert story points to hours, based on research and industry best practices.

## Overview

The tool provides four different estimation approaches to calculate hours from story points:

1. **Current (AI-generated)** - Direct AI estimation based on work item analysis
2. **Exponential Model** - Research-backed non-linear growth
3. **Power Model** - Alternative non-linear approach
4. **Fibonacci Ranges Model** - Industry standard with uncertainty ranges

## Why Non-Linear Estimation?

### The Problem with Linear Mapping

Traditional linear mapping (1 SP = X hours) is fundamentally flawed because:

- **Uncertainty scales non-linearly**: Larger stories have disproportionately higher uncertainty
- **Complexity compounds**: A 13-point story is NOT ~13x the work of a 1-point story
- **Integration overhead**: Multi-component stories have coordination overhead
- **Risk amplification**: Larger stories carry more risk of unknown unknowns

### Research Evidence

Studies show that software effort follows non-linear patterns:
- [McConnell's Cone of Uncertainty](https://www.stevemcconnell.com/articles/cou.htm): Uncertainty grows exponentially with project size
- [COCOMO models](https://en.wikipedia.org/wiki/COCOMO): Effort = a × (Size)^b where b > 1
- [Agile estimation research](https://agileforall.com/2024/02/story-points-hours-conversion-anti-pattern/): Direct SP→hours conversion is an anti-pattern

## Estimation Models

### 1. Exponential Model (Recommended)

**Formula**: `Hours = BaseHours × e^(k × (SP-1))`

**Parameters**:
- `BaseHours`: Hours for 1 story point (configurable)
- `k`: Growth rate factor (default: 0.3, range: 0.2-0.4)

**Why it works**:
- Reflects compounding complexity
- Small stories grow slowly, large stories grow rapidly
- Matches real-world experience

**Example** (BaseHours=4, k=0.3):
- 1 SP = 4 hours
- 3 SP = 7 hours
- 5 SP = 13 hours
- 8 SP = 33 hours
- 13 SP = 146 hours

### 2. Power Model

**Formula**: `Hours = a × SP^b`

**Parameters**:
- `a`: Base multiplier (default: 3.0)
- `b`: Power exponent (default: 1.2, must be >1)

**Why it works**:
- Good for medium to large stories
- Simpler than exponential but still non-linear
- Based on traditional software estimation models

**Example** (a=3, b=1.2):
- 1 SP = 3 hours
- 3 SP = 11 hours
- 5 SP = 21 hours
- 8 SP = 36 hours
- 13 SP = 65 hours

### 3. Fibonacci Ranges Model (Industry Standard)

**Approach**: Map story points to Fibonacci-based hour ranges

**Why it works**:
- Fibonacci sequence naturally represents increasing uncertainty
- Each number is roughly the sum of previous two
- Industry standard for agile estimation

**Base Ranges** (for BaseHours=4):
| Story Points | Min Hours | Expected Hours | Max Hours |
|--------------|-----------|----------------|-----------|
| 1            | 3         | 4              | 5         |
| 2            | 5         | 6              | 8         |
| 3            | 8         | 10             | 13        |
| 5            | 13        | 17             | 21        |
| 8            | 21        | 27             | 34        |
| 13           | 34        | 44             | 55        |

### 4. Linear Model (Baseline)

**Formula**: `Hours = SP × BaseHours`

**Purpose**: Reference for comparison, shows the limitation of linear thinking

## Uncertainty Handling

All models apply uncertainty buffers:
- **Min Hours**: `Expected × 0.6` (40% buffer under)
- **Max Hours**: `Expected × 1.8` (80% buffer over)

This reflects the "cone of uncertainty" where:
- Small stories have relatively narrow ranges
- Large stories have very wide ranges
- Reality often falls between but with bias toward overruns

## Configuration

### Basic Configuration

Create a `config.yml` file:

```yaml
hours_estimation:
  base_hours_per_point: 4.0        # Team-specific velocity
  uncertainty_factor_min: 0.6      # Conservative underestimation
  uncertainty_factor_max: 1.8      # Generous overestimation
  exponential_k: 0.3               # Exponential growth rate
  power_a: 3.0                     # Power model base
  power_b: 1.2                     # Power model exponent
```

### Team Velocity Calibration

Determine your `base_hours_per_point`:

1. **Track completed stories**: Record actual hours vs story points
2. **Calculate velocity**: Total hours ÷ Total story points
3. **Adjust for context**:
   - Simple work: 2-4 hours per SP
   - Average complexity: 4-6 hours per SP
   - Complex domain: 6-8 hours per SP

### Environment-Specific Adjustments

```yaml
# For fast-moving teams with senior developers
hours_estimation:
  base_hours_per_point: 3.0

# For enterprise teams with overhead
hours_estimation:
  base_hours_per_point: 6.0
  uncertainty_factor_max: 2.0

# For research/prototype work
hours_estimation:
  base_hours_per_point: 5.0
  uncertainty_factor_max: 2.5
```

## Usage

### Command Line

```bash
# Show all estimation approaches
python main.py \
  --docs-dir docs/ \
  --fe-dir frontend/ \
  --be-dir backend/ \
  --show-all-estimates

# With custom configuration
python main.py \
  --docs-dir docs/ \
  --fe-dir frontend/ \
  --be-dir backend/ \
  --config custom-config.yml \
  --show-all-estimates
```

### Output Format

```
================================================================================
HOURS ESTIMATION APPROACHES COMPARISON
================================================================================

Overall (5 SP):
  Model                     Min Hours Expected  Max Hours
-----------------------------------------------------------------
  Linear Model (Baseline)   12        20        36
  Exponential Model         8         13        24
  Power Model               12        21        37
  Fibonacci Ranges Model    13        17        21

FRONTEND (3 SP):
  Model                     Min Hours Expected  Max Hours
-----------------------------------------------------------------
  Linear Model (Baseline)   7         12        22
  Exponential Model         4         7         13
  Power Model               7         11        20
  Fibonacci Ranges Model    8         10        13
```

## Model Selection Guidelines

### When to Use Each Model

**Exponential Model**:
- Default choice for most teams
- Best for projects with high complexity growth
- When integration overhead is significant

**Power Model**:
- Medium to large stories (3+ SP)
- When complexity is predictable but non-linear
- Good balance of simplicity and accuracy

**Fibonacci Ranges**:
- Teams already using Fibonacci for estimation
- When uncertainty communication is important
- Conservative approach for risk-averse teams

**Linear Model**:
- Only for very small stories (1-2 SP)
- Educational purposes to show limitation
- When work is highly repetitive and predictable

### Combining Models

For best results, consider:

1. **Consensus Approach**: Take the average of non-linear models
2. **Range Overlay**: Use the widest range from all models
3. **Context-Specific**: Use different models for different types of work

## Best Practices

### 1. Track Actuals
Always record actual hours vs estimates:
```yaml
# In your project tracking
stories_completed:
  - story_points: 3
    estimated_hours: [8, 13, 11, 10]  # All models
    actual_hours: 12
    lessons: Integration took longer
```

### 2. Update Quarterly
Re-calibrate base hours quarterly based on:
- Team composition changes
- Technology stack updates
- Process improvements

### 3. Use Probabilistic Thinking
- Never give exact hours, always provide ranges
- Communicate confidence levels
- Plan for the 80% case, not the 50%

### 4. Account for Context
Adjust for:
- Team experience with domain
- Codebase health (technical debt)
- External dependencies
- Seasonal factors (holidays, etc.)

## Common Pitfalls

### 1. Ignoring Team Velocity
Don't use default 4 hours per SP if your team is different.

### 2. Single Point Estimates
Always provide ranges, never single numbers.

### 3. Not Updating Models
Teams change, tools improve, update your base hours.

### 4. Ignoring Risk Factors
Add buffers for:
- Unknown requirements
- Technical uncertainty
- External dependencies

## Research References

1. **Cone of Uncertainty** - Barry Boehm, Steve McConnell
2. **COCOMO II Model** - Constructive Cost Model
3. **Function Point Analysis** - IFPUG standards
4. **Agile Estimation Techniques** - Mike Cohn
5. **Software Engineering Economics** - Capers Jones

## Conclusion

Non-linear estimation better reflects the reality of software development. The key is to:

1. **Choose a model** that fits your context
2. **Calibrate base hours** for your team
3. **Use ranges** not point estimates
4. **Track and adjust** based on actuals
5. **Communicate uncertainty** to stakeholders

Remember: The goal isn't perfect prediction, but better planning through understanding uncertainty.