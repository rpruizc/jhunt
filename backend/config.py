"""
Configuration module for Job Role Matcher.
Loads and validates configuration from YAML file using Pydantic models.
"""

from pydantic import BaseModel, Field
from typing import List
import yaml
import os


class GeographyConfig(BaseModel):
    """Geography preferences for job matching."""
    preferred: List[str] = Field(default_factory=list)
    banned: List[str] = Field(default_factory=list)


class ScoringWeights(BaseModel):
    """Weights for each scoring dimension."""
    seniority: int = 30
    pnl: int = 20
    transformation: int = 20
    industry: int = 20
    geo: int = 10
    banned_penalty: int = 10


class CompanyConfig(BaseModel):
    """Configuration for a target company."""
    name: str
    careers_url: str
    adapter: str


class Config(BaseModel):
    """Main configuration model."""
    admin_token: str
    companies: List[CompanyConfig]
    seniority_keywords: List[str] = Field(default_factory=list)
    domain_keywords: List[str] = Field(default_factory=list)
    geography: GeographyConfig
    scoring_weights: ScoringWeights = Field(default_factory=ScoringWeights)


def load_config(path: str = "config.yaml") -> Config:
    """
    Load and validate configuration from YAML file.
    
    Args:
        path: Path to configuration file (default: config.yaml)
        
    Returns:
        Validated Config object
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML syntax is invalid
        pydantic.ValidationError: If config structure is invalid
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Configuration file not found: {path}\n"
            f"Please copy config.example.yaml to {path} and customize it."
        )
    
    try:
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(
            f"Invalid YAML syntax in {path}: {e}"
        )
    
    if data is None:
        raise ValueError(f"Configuration file {path} is empty")
    
    try:
        config = Config(**data)
    except Exception as e:
        raise ValueError(
            f"Invalid configuration structure in {path}: {e}\n"
            f"Please check config.example.yaml for the correct format."
        )
    
    return config
