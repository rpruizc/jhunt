"""
Company adapter registry.

This module maintains a registry of all available company adapters.
Use get_adapter() to retrieve an adapter instance by name.
"""

from typing import Dict, Type
from scraper.base import BaseAdapter
from scraper.adapters.siemens import SiemensAdapter
from scraper.adapters.bosch import BoschAdapter
from scraper.adapters.abb import ABBAdapter


# Registry of available adapters
# Maps adapter name (from config) to adapter class
ADAPTERS: Dict[str, Type[BaseAdapter]] = {
    "siemens": SiemensAdapter,
    "bosch": BoschAdapter,
    "abb": ABBAdapter,
}


def get_adapter(company_config) -> BaseAdapter:
    """
    Get adapter instance for a company.
    
    Args:
        company_config: CompanyConfig object with adapter name
        
    Returns:
        Instantiated adapter for the company
        
    Raises:
        ValueError: If adapter name is not registered
    """
    adapter_class = ADAPTERS.get(company_config.adapter)
    if not adapter_class:
        raise ValueError(
            f"Unknown adapter: {company_config.adapter}. "
            f"Available adapters: {', '.join(ADAPTERS.keys())}"
        )
    return adapter_class(company_config)
