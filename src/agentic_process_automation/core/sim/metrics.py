from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional, Any, Literal


SampleMode = Literal["periodic", "posthoc"]


@dataclass(frozen=True)
class Metric:
    """Description of a metric and how to calculate it.

    - sampler: called as sampler(time_hr, run_result_dict). For posthoc metrics, time_hr will be None.
    - sample_mode: "periodic" samples at chosen times across the simulation; "posthoc" computes once per run.
    - frequency_hz: optional samples per hour; if provided, overrides target_samples for this metric.
    - target_samples: optional target number of samples across the full duration; defaults to ~50 if not provided.
    - aggregate_across_simulations: optional reducer to combine values across simulations (not used by simulate);
      visualizers or callers can use it for aggregated displays.
    """

    name: str
    sampler: Callable[[Optional[float], dict], Any]
    sample_mode: SampleMode = "periodic"
    frequency_hz: Optional[float] = None
    target_samples: Optional[int] = None
    aggregate_across_simulations: Optional[Callable[[list[Any]], Any]] = None
