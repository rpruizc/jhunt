"""
Signal dataclasses for job scoring.
Each signal represents a dimension of job fit with score and evidence.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SenioritySignal:
    """Signal for seniority level match."""
    level: str  # VP, Senior Director, Director, Other
    score: int  # 0-30 points


@dataclass
class PnLSignal:
    """Signal for P&L ownership."""
    score: int  # 0-20 points
    evidence: Optional[str] = None  # Text snippet showing P&L mention


@dataclass
class TransformationSignal:
    """Signal for transformation mandate."""
    score: int  # 0-20 points
    evidence: Optional[str] = None  # Text snippet showing transformation mention


@dataclass
class IndustrySignal:
    """Signal for industry match."""
    score: int  # 0-20 points
    evidence: Optional[str] = None  # Text snippet showing industry keywords


@dataclass
class GeoSignal:
    """Signal for geographic scope."""
    score: int  # 0-10 points
    is_banned: bool = False  # True if location is in banned geographies
    evidence: Optional[str] = None  # Text snippet showing geography mention
