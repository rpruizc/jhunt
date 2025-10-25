"""
Base adapter interface for company job scrapers.

Every adapter MUST:
1. Fill external_id with the company's unique requisition ID or job identifier
2. Fill url with the canonical link to the job posting
3. Set partial_description=True if the description is truncated or incomplete
4. Return empty list on failure rather than raising exception (runner handles errors)
5. Implement timeout-safe HTTP requests (use requests with timeout parameter)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class RawJobPosting:
    """
    Raw job posting data from company careers system.
    
    Attributes:
        external_id: Company's unique requisition ID or job identifier (REQUIRED)
        title: Job title (REQUIRED)
        location: Job location (REQUIRED)
        description: Full job description text (REQUIRED)
        url: Canonical link to the job posting (REQUIRED)
        partial_description: True if description is truncated or incomplete (default: False)
        department: Department or business unit (optional)
    """
    external_id: str
    title: str
    location: str
    description: str
    url: str
    partial_description: bool = False
    department: Optional[str] = None


class BaseAdapter(ABC):
    """
    Abstract base class for company-specific job scrapers.
    
    Each adapter is responsible for fetching job postings from a single company's
    careers system (API or HTML scraping).
    """
    
    def __init__(self, company_config):
        """
        Initialize adapter with company configuration.
        
        Args:
            company_config: CompanyConfig object with name, careers_url, adapter
        """
        self.company = company_config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def fetch_jobs(self) -> List[RawJobPosting]:
        """
        Fetch jobs from company careers system.
        
        Returns:
            List of RawJobPosting objects. Returns empty list on failure.
            
        Notes:
            - MUST NOT raise exceptions - return empty list and log errors instead
            - MUST set external_id to company's unique job identifier
            - MUST set url to canonical job posting link
            - MUST set partial_description=True if full text unavailable
            - SHOULD use requests with timeout parameter (recommended: 20 seconds)
            - SHOULD log errors for debugging
        """
        raise NotImplementedError
