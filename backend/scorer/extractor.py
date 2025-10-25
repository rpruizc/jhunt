"""
Signal extraction module for job scoring.
Extracts signals from job postings based on keywords and patterns.
"""

from typing import List, Optional
from .signals import (
    SenioritySignal,
    PnLSignal,
    TransformationSignal,
    IndustrySignal,
    GeoSignal
)
from config import Config


class SignalExtractor:
    """Extracts scoring signals from job postings."""
    
    def __init__(self, config: Config):
        """
        Initialize signal extractor with configuration.
        
        Args:
            config: Configuration object with keywords and weights
        """
        self.config = config
    
    def extract_seniority(self, title: str) -> SenioritySignal:
        """
        Parse job title for seniority level.
        
        Args:
            title: Job title string
            
        Returns:
            SenioritySignal with level and score
        """
        title_lower = title.lower()
        
        # VP level: 30 points
        if any(kw in title_lower for kw in ["vp", "vice president"]):
            return SenioritySignal(level="VP", score=30)
        
        # Senior Director: 25 points
        elif any(kw in title_lower for kw in ["senior director", "sr director", "sr. director"]):
            return SenioritySignal(level="Senior Director", score=25)
        
        # Director: 20 points
        elif "director" in title_lower:
            return SenioritySignal(level="Director", score=20)
        
        # Other: 0 points
        return SenioritySignal(level="Other", score=0)
    
    def _extract_evidence(
        self,
        text: str,
        keywords: List[str],
        window: int = 80
    ) -> Optional[str]:
        """
        Extract short text snippet around first matching keyword.
        
        Args:
            text: Text to search in
            keywords: List of keywords to search for
            window: Number of characters before and after keyword (default: 80)
            
        Returns:
            Text snippet with ellipsis if truncated, or None if no match
        """
        text_lower = text.lower()
        
        for kw in keywords:
            kw_lower = kw.lower()
            idx = text_lower.find(kw_lower)
            
            if idx != -1:
                # Calculate snippet boundaries
                start = max(idx - window, 0)
                end = min(idx + len(kw) + window, len(text))
                
                # Extract snippet from original text (preserve case)
                snippet = text[start:end].strip()
                
                # Add ellipsis if truncated
                if start > 0:
                    snippet = "..." + snippet
                if end < len(text):
                    snippet = snippet + "..."
                
                return snippet
        
        return None
    
    def extract_pnl_signals(self, description: str) -> PnLSignal:
        """
        Search description for P&L ownership keywords.
        
        Args:
            description: Job description text
            
        Returns:
            PnLSignal with score and evidence
        """
        desc_lower = description.lower()
        
        # Strong keywords: 20 points
        strong_keywords = [
            "p&l", "p & l", "profit and loss",
            "profitability", "ebitda",
            "budget control", "cost reduction",
            "financial accountability"
        ]
        
        # Medium keywords: 15 points
        medium_keywords = [
            "commercial growth", "revenue targets",
            "portfolio margin", "revenue growth",
            "business results", "financial performance"
        ]
        
        # Check for strong keywords first
        if any(kw in desc_lower for kw in strong_keywords):
            evidence = self._extract_evidence(description, strong_keywords)
            return PnLSignal(score=20, evidence=evidence)
        
        # Check for medium keywords
        elif any(kw in desc_lower for kw in medium_keywords):
            evidence = self._extract_evidence(description, medium_keywords)
            return PnLSignal(score=15, evidence=evidence)
        
        # No P&L signals found
        return PnLSignal(score=0, evidence=None)
    
    def extract_transformation_signals(self, description: str) -> TransformationSignal:
        """
        Search description for transformation mandate keywords.
        
        Args:
            description: Job description text
            
        Returns:
            TransformationSignal with score and evidence
        """
        desc_lower = description.lower()
        
        # Transformation keywords: 20 points
        transformation_keywords = [
            "digital transformation",
            "erp modernization", "erp implementation",
            "post-acquisition integration", "post acquisition integration",
            "operational transformation",
            "technology roadmap",
            "business transformation",
            "modernization", "digitalization",
            "system integration"
        ]
        
        # Check for transformation keywords
        if any(kw in desc_lower for kw in transformation_keywords):
            evidence = self._extract_evidence(description, transformation_keywords)
            return TransformationSignal(score=20, evidence=evidence)
        
        # No transformation signals found
        return TransformationSignal(score=0, evidence=None)
    
    def extract_industry_signals(self, description: str) -> IndustrySignal:
        """
        Search description for industry match keywords.
        
        Args:
            description: Job description text
            
        Returns:
            IndustrySignal with score and evidence
        """
        desc_lower = description.lower()
        
        # Strong industry match keywords: 20 points
        strong_industry_keywords = [
            "industrial iot", "iiot",
            "factory automation", "manufacturing automation",
            "electrification", "ev batteries", "battery",
            "energy systems", "energy storage",
            "regulated environments", "regulated industry",
            "industry 4.0", "smart manufacturing",
            "industrial ai", "predictive maintenance",
            "scada", "plc", "mes"
        ]
        
        # Adjacent software keywords: 10 points
        adjacent_keywords = [
            "enterprise software", "saas platform",
            "cloud infrastructure", "data analytics",
            "machine learning", "artificial intelligence"
        ]
        
        # Check for strong industry match first
        if any(kw in desc_lower for kw in strong_industry_keywords):
            evidence = self._extract_evidence(description, strong_industry_keywords)
            return IndustrySignal(score=20, evidence=evidence)
        
        # Check for adjacent software roles
        elif any(kw in desc_lower for kw in adjacent_keywords):
            evidence = self._extract_evidence(description, adjacent_keywords)
            return IndustrySignal(score=10, evidence=evidence)
        
        # No industry signals found
        return IndustrySignal(score=0, evidence=None)
    
    def extract_geo_signals(self, description: str, location: str) -> GeoSignal:
        """
        Check description and location for preferred/banned geographies.
        
        Args:
            description: Job description text
            location: Job location string
            
        Returns:
            GeoSignal with score, banned flag, and evidence
        """
        desc_lower = description.lower()
        location_lower = location.lower()
        combined = desc_lower + " " + location_lower
        
        score = 0
        is_banned = False
        evidence = None
        
        # Check for preferred geographies: 10 points
        preferred = self.config.geography.preferred
        for geo in preferred:
            geo_lower = geo.lower()
            if geo_lower in combined:
                score = 10
                # Try to extract evidence from description first, then location
                evidence = self._extract_evidence(description, [geo])
                if not evidence:
                    evidence = f"Location: {location}"
                break
        
        # Check for banned geographies
        banned = self.config.geography.banned
        for geo in banned:
            geo_lower = geo.lower()
            if geo_lower in combined:
                is_banned = True
                # Try to extract evidence from description first, then location
                ban_evidence = self._extract_evidence(description, [geo])
                if not ban_evidence:
                    ban_evidence = f"Location: {location}"
                evidence = ban_evidence
                break
        
        return GeoSignal(score=score, is_banned=is_banned, evidence=evidence)
