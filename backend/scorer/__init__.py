"""
Scorer package for job role matching.
Provides signal extraction and scoring functionality.
"""

from .engine import ScoringEngine, Evaluation
from .extractor import SignalExtractor
from .signals import (
    SenioritySignal,
    PnLSignal,
    TransformationSignal,
    IndustrySignal,
    GeoSignal
)

__all__ = [
    'ScoringEngine',
    'Evaluation',
    'SignalExtractor',
    'SenioritySignal',
    'PnLSignal',
    'TransformationSignal',
    'IndustrySignal',
    'GeoSignal',
]
