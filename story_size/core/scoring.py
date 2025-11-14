from typing import Dict, List
from story_size.core.models import Factors

def calculate_complexity_score(factors: Factors, weights: Dict[str, int]) -> int:
    """
    Calculates the complexity score based on the factors and weights.
    """
    return (
        weights.get("DC", 1) * factors.dc +
        weights.get("IC", 1) * factors.ic +
        weights.get("IB", 1) * factors.ib +
        weights.get("DS", 1) * factors.ds +
        weights.get("NR", 1) * factors.nr
    )

def map_to_story_points(score: int, mapping: Dict[str, int]) -> int:
    """
    Maps the complexity score to story points.
    """
    if score <= mapping.get("sp1_max", 7):
        return 1
    elif score <= mapping.get("sp2_max", 10):
        return 2
    elif score <= mapping.get("sp3_max", 13):
        return 3
    elif score <= mapping.get("sp5_max", 16):
        return 5
    elif score <= mapping.get("sp8_max", 20):
        return 8
    else:
        return 13

def get_confidence(factors: Factors) -> float:
    """
    Calculates a confidence score based on the factor values.
    This is a simple implementation and can be improved.
    """
    # Simple confidence calculation: closer to the average, higher the confidence
    avg_factor = (factors.dc + factors.ic + factors.ib + factors.ds + factors.nr) / 5.0
    variance = sum([(x - avg_factor) ** 2 for x in [factors.dc, factors.ic, factors.ib, factors.ds, factors.nr]]) / 5.0
    return 1.0 - (variance / 4.0) # Normalize to a 0-1 range, assuming max variance is 4 (for 1-5 range)
