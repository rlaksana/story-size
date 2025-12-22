"""Non-linear estimation models for converting story points to hours"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
import math


@dataclass
class EstimationModel:
    """Represents an estimation model with its parameters"""
    name: str
    description: str
    min_hours: int
    max_hours: int
    expected_hours: int


class NonLinearEstimator:
    """Implements various non-linear estimation models based on research"""

    def __init__(self, base_hours_per_point: float = None, config: dict = None):
        """
        Initialize estimator with configurable base hours per story point

        Args:
            base_hours_per_point: Hours for 1 story point (varies by team)
            config: Configuration dictionary for estimation settings
        """
        # Load from config if provided
        if config:
            estimation_config = config.get("hours_estimation", {})
            self.base_hours_per_point = estimation_config.get("base_hours_per_point", base_hours_per_point or 4.0)
            self.uncertainty_factor_min = estimation_config.get("uncertainty_factor_min", 0.6)
            self.uncertainty_factor_max = estimation_config.get("uncertainty_factor_max", 1.8)
            self.exponential_k = estimation_config.get("exponential_k", 0.3)
            self.power_a = estimation_config.get("power_a", 3.0)
            self.power_b = estimation_config.get("power_b", 1.2)
        else:
            self.base_hours_per_point = base_hours_per_point or 4.0
            # Default uncertainty factors based on research
            self.uncertainty_factor_min = 0.6  # 40% buffer under
            self.uncertainty_factor_max = 1.8  # 80% buffer over
            self.exponential_k = 0.3
            self.power_a = 3.0
            self.power_b = 1.2

    def exponential_model(self, story_points: int, k: float = None) -> EstimationModel:
        """
        Exponential growth model: Hours = BaseHours × e^(k × StoryPoints)

        Most recommended by research for reflecting compounding complexity

        Args:
            story_points: Number of story points
            k: Growth rate factor (0.2-0.4 recommended)
        """
        if k is None:
            k = self.exponential_k
        expected_hours = self.base_hours_per_point * math.exp(k * (story_points - 1))
        min_hours = expected_hours * self.uncertainty_factor_min
        max_hours = expected_hours * self.uncertainty_factor_max

        return EstimationModel(
            name="Exponential Model",
            description=f"Hours = {self.base_hours_per_point} × e^{k}^(SP-1) where k={k}",
            min_hours=round(min_hours),
            max_hours=round(max_hours),
            expected_hours=round(expected_hours)
        )

    def power_model(self, story_points: int, a: float = None, b: float = None) -> EstimationModel:
        """
        Power function model: Hours = a × StoryPoints^b

        Good for medium to large stories

        Args:
            story_points: Number of story points
            a: Base multiplier (typically 2-4)
            b: Power exponent (>1 for non-linear, typically 1.1-1.4)
        """
        if a is None:
            a = self.power_a
        if b is None:
            b = self.power_b
        expected_hours = a * (story_points ** b)
        min_hours = expected_hours * self.uncertainty_factor_min
        max_hours = expected_hours * self.uncertainty_factor_max

        return EstimationModel(
            name="Power Model",
            description=f"Hours = {a} × SP^{b}",
            min_hours=round(min_hours),
            max_hours=round(max_hours),
            expected_hours=round(expected_hours)
        )

    def fibonacci_ranges_model(self, story_points: int) -> EstimationModel:
        """
        Fibonacci-based ranges (Industry Standard)

        Based on uncertainty cone and industry practices.
        Each Fibonacci number represents increasing uncertainty.
        """
        # Fibonacci-based hour ranges from research
        fibonacci_ranges = {
            1: (3, 5),     # 3-5 hours
            2: (5, 8),     # 5-8 hours
            3: (8, 13),    # 8-13 hours
            5: (13, 21),   # 13-21 hours
            8: (21, 34),   # 21-34 hours
            13: (34, 55),  # 34-55 hours
            21: (55, 89),  # 55-89 hours
            40: (89, 144), # 89-144 hours
            100: (144, 233) # 144-233 hours
        }

        # Find closest Fibonacci number
        fibonacci_sequence = [1, 2, 3, 5, 8, 13, 21, 40, 100]
        closest_fib = min(fibonacci_sequence, key=lambda x: abs(x - story_points))

        min_hours, max_hours = fibonacci_ranges.get(closest_fib, (3, 5))
        expected_hours = (min_hours + max_hours) // 2

        # Apply team velocity factor
        velocity_factor = self.base_hours_per_point / 4.0  # 4.0 is default base
        min_hours = round(min_hours * velocity_factor)
        max_hours = round(max_hours * velocity_factor)
        expected_hours = round(expected_hours * velocity_factor)

        return EstimationModel(
            name="Fibonacci Ranges Model",
            description=f"Based on {closest_fib} Fibonacci point (scaled to team velocity)",
            min_hours=min_hours,
            max_hours=max_hours,
            expected_hours=expected_hours
        )

    def linear_model(self, story_points: int) -> EstimationModel:
        """
        Simple linear model for comparison

        Args:
            story_points: Number of story points
        """
        expected_hours = story_points * self.base_hours_per_point
        min_hours = expected_hours * self.uncertainty_factor_min
        max_hours = expected_hours * self.uncertainty_factor_max

        return EstimationModel(
            name="Linear Model (Baseline)",
            description=f"Hours = SP × {self.base_hours_per_point}",
            min_hours=round(min_hours),
            max_hours=round(max_hours),
            expected_hours=round(expected_hours)
        )

    def calculate_all_models(self, story_points: int) -> List[EstimationModel]:
        """
        Calculate hours using all estimation models

        Args:
            story_points: Number of story points

        Returns:
            List of all estimation models
        """
        models = [
            self.linear_model(story_points),
            self.exponential_model(story_points),
            self.power_model(story_points),
            self.fibonacci_ranges_model(story_points)
        ]
        return models

    def get_recommended_range(self, story_points: int) -> Tuple[int, int]:
        """
        Get recommended hours range based on consensus of non-linear models

        Args:
            story_points: Number of story points

        Returns:
            Tuple of (min_hours, max_hours)
        """
        models = self.calculate_all_models(story_points)

        # Exclude linear model from recommendation
        non_linear_models = models[1:]

        # Calculate consensus range
        min_hours = min(m.min_hours for m in non_linear_models)
        max_hours = max(m.max_hours for m in non_linear_models)

        return (min_hours, max_hours)

    def format_models_comparison(self, story_points: int) -> str:
        """
        Format all models as a comparison table

        Args:
            story_points: Number of story points

        Returns:
            Formatted comparison table
        """
        models = self.calculate_all_models(story_points)

        lines = []
        lines.append("=" * 80)
        lines.append(f"HOURS ESTIMATION COMPARISON for {story_points} Story Points")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Base Configuration: {self.base_hours_per_point} hours per story point")
        lines.append("")

        # Table header
        lines.append(f"{'Model':<25} {'Min Hours':<12} {'Expected':<12} {'Max Hours':<12} {'Description'}")
        lines.append("-" * 80)

        # Table rows
        for model in models:
            description = model.description[:40] + "..." if len(model.description) > 40 else model.description
            lines.append(f"{model.name:<25} {model.min_hours:<12} {model.expected_hours:<12} {model.max_hours:<12} {description}")

        lines.append("")
        lines.append("=" * 80)

        # Recommendation
        recommended_min, recommended_max = self.get_recommended_range(story_points)
        lines.append(f"RECOMMENDED RANGE: {recommended_min}-{recommended_max} hours")
        lines.append("(Based on consensus of non-linear models)")
        lines.append("=" * 80)

        return "\n".join(lines)