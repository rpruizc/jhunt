"""
Scoring engine for job role matching.
Calculates fit scores and generates evaluation summaries.
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from .extractor import SignalExtractor
from .signals import (
    SenioritySignal,
    PnLSignal,
    TransformationSignal,
    IndustrySignal,
    GeoSignal
)
from config import Config


@dataclass
class Evaluation:
    """Evaluation result for a job posting."""
    job_id: int
    fit_score: int
    seniority_score: int
    pnl_score: int
    transformation_score: int
    industry_score: int
    geo_score: int
    action: str
    summary: str
    concerns: List[Dict[str, str]]


class ScoringEngine:
    """Calculates fit scores and generates evaluations for job postings."""
    
    def __init__(self, config: Config, extractor: SignalExtractor):
        """
        Initialize scoring engine.
        
        Args:
            config: Configuration object with scoring weights
            extractor: SignalExtractor instance for extracting signals
        """
        self.config = config
        self.extractor = extractor
    
    def score_job(self, job: Dict[str, Any]) -> Evaluation:
        """
        Calculate fit score and generate evaluation for a job posting.
        
        Args:
            job: Job dictionary with id, title, location, description, company_name, partial_description
            
        Returns:
            Evaluation object ready for database insert
        """
        # Extract all signals
        seniority = self.extractor.extract_seniority(job['title'])
        pnl = self.extractor.extract_pnl_signals(job['description'])
        transformation = self.extractor.extract_transformation_signals(job['description'])
        industry = self.extractor.extract_industry_signals(job['description'])
        geo = self.extractor.extract_geo_signals(job['description'], job['location'])
        
        # Calculate total score using config weights
        # Normalize each dimension by its max points
        weights = self.config.scoring_weights
        total_score = (
            (seniority.score / 30) * weights.seniority +
            (pnl.score / 20) * weights.pnl +
            (transformation.score / 20) * weights.transformation +
            (industry.score / 20) * weights.industry +
            (geo.score / 10) * weights.geo
        )
        
        # Apply geography penalty if needed
        if geo.is_banned:
            total_score -= weights.banned_penalty
        
        # Clamp to 0-100 range
        total_score = max(0, min(100, int(total_score)))
        
        # Determine action label
        action = self._determine_action(total_score)
        
        # Generate concerns
        concerns = self._generate_concerns(
            job, seniority, pnl, transformation, industry, geo
        )
        
        # Generate summary
        summary = self._generate_summary(
            job, seniority, pnl, transformation, industry, geo, action, total_score
        )
        
        return Evaluation(
            job_id=job['id'],
            fit_score=total_score,
            seniority_score=seniority.score,
            pnl_score=pnl.score,
            transformation_score=transformation.score,
            industry_score=industry.score,
            geo_score=geo.score,
            action=action,
            summary=summary,
            concerns=concerns
        )
    
    def _determine_action(self, score: int) -> str:
        """
        Determine action label based on fit score.
        
        Args:
            score: Fit score (0-100)
            
        Returns:
            Action label: 'APPLY', 'WATCH', or 'SKIP'
        """
        if score >= 75:
            return "APPLY"
        elif score >= 60:
            return "WATCH"
        return "SKIP"
    
    def _generate_concerns(
        self,
        job: Dict[str, Any],
        seniority: SenioritySignal,
        pnl: PnLSignal,
        transformation: TransformationSignal,
        industry: IndustrySignal,
        geo: GeoSignal
    ) -> List[Dict[str, str]]:
        """
        Generate concerns with evidence from job description.
        
        Args:
            job: Job dictionary
            seniority: Seniority signal
            pnl: P&L signal
            transformation: Transformation signal
            industry: Industry signal
            geo: Geography signal
            
        Returns:
            List of concern dictionaries with 'type' and 'evidence' keys
        """
        concerns = []
        
        # Below target seniority
        if seniority.score < 20:
            concerns.append({
                "type": "Below target seniority",
                "evidence": f"Title: {job['title']}"
            })
        
        # No P&L ownership
        if pnl.score == 0:
            concerns.append({
                "type": "No P&L ownership",
                "evidence": "No mention of P&L, profitability, or budget control"
            })
        
        # No transformation mandate
        if transformation.score == 0:
            concerns.append({
                "type": "No transformation mandate",
                "evidence": "No mention of digital transformation or modernization"
            })
        
        # No industry match
        if industry.score < 10:
            concerns.append({
                "type": "No industry match",
                "evidence": "No mention of industrial IoT, manufacturing, or hardware"
            })
        
        # Banned geography
        if geo.is_banned:
            concerns.append({
                "type": "Banned geography",
                "evidence": geo.evidence or f"Location: {job['location']}"
            })
        
        # Incomplete description
        if job.get('partial_description', False):
            concerns.append({
                "type": "Incomplete description",
                "evidence": "Full job description text not available"
            })
        
        return concerns
    
    def _generate_summary(
        self,
        job: Dict[str, Any],
        seniority: SenioritySignal,
        pnl: PnLSignal,
        transformation: TransformationSignal,
        industry: IndustrySignal,
        geo: GeoSignal,
        action: str,
        score: int
    ) -> str:
        """
        Generate structured summary text.
        
        Args:
            job: Job dictionary
            seniority: Seniority signal
            pnl: P&L signal
            transformation: Transformation signal
            industry: Industry signal
            geo: Geography signal
            action: Action label
            score: Fit score
            
        Returns:
            Summary text following template structure
        """
        # Identify top 2 strengths
        strengths = []
        
        if pnl.score >= 15:
            strengths.append("P&L ownership")
        if transformation.score >= 20:
            strengths.append("transformation mandate")
        if industry.score >= 20:
            strengths.append("industry match")
        if geo.score >= 10:
            strengths.append("geographic scope")
        if seniority.score >= 25:
            strengths.append("senior level")
        
        top_strengths = ", ".join(strengths[:2]) if strengths else "none"
        
        # Identify top concern (gap)
        top_concern = "none"
        if seniority.score < 20:
            top_concern = "below target seniority"
        elif pnl.score == 0:
            top_concern = "no P&L ownership"
        elif transformation.score == 0:
            top_concern = "no transformation mandate"
        elif industry.score < 10:
            top_concern = "no industry match"
        elif geo.is_banned:
            top_concern = "banned geography"
        
        return (
            f"Role: {job['title']} at {job['company_name']} in {job['location']}. "
            f"Fit: {top_strengths}. "
            f"Gap: {top_concern}. "
            f"Action: {action}. "
            f"Score: {score}."
        )
