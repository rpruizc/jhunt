"""
Siemens adapter for fetching job postings.

Siemens provides a careers API that returns job data in JSON format.
"""

import requests
from typing import List
from scraper.base import BaseAdapter, RawJobPosting


class SiemensAdapter(BaseAdapter):
    """Adapter for Siemens careers API."""
    
    def fetch_jobs(self) -> List[RawJobPosting]:
        """
        Fetch jobs from Siemens careers API.
        
        Returns:
            List of RawJobPosting objects, empty list on failure
        """
        try:
            # Siemens typically has a JSON API endpoint
            # This is a template - actual URL structure may vary
            response = requests.get(
                self.company.careers_url,
                timeout=20,
                headers={'User-Agent': 'JobRoleMatcher/1.0'}
            )
            response.raise_for_status()
            
            data = response.json()
            jobs = []
            
            # Parse response structure
            # Actual structure depends on Siemens API format
            job_listings = data.get('jobs', []) if isinstance(data, dict) else data
            
            for job_data in job_listings:
                # Extract required fields
                external_id = str(job_data.get('id') or job_data.get('requisitionId', ''))
                title = job_data.get('title', '')
                location = job_data.get('location', '')
                description = job_data.get('description', '')
                url = job_data.get('url', '') or job_data.get('applyUrl', '')
                department = job_data.get('department')
                
                # Skip if missing required fields
                if not all([external_id, title, location, description, url]):
                    self.logger.warning(
                        f"Skipping job with missing fields: id={external_id}, title={title}"
                    )
                    continue
                
                # Check if description is truncated
                partial_description = len(description) < 100 or 'read more' in description.lower()
                
                jobs.append(RawJobPosting(
                    external_id=external_id,
                    title=title,
                    location=location,
                    description=description,
                    url=url,
                    partial_description=partial_description,
                    department=department
                ))
            
            self.logger.info(f"Fetched {len(jobs)} jobs from Siemens")
            return jobs
            
        except requests.exceptions.Timeout:
            self.logger.error(f"Timeout fetching jobs from {self.company.name}")
            return []
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error fetching jobs from {self.company.name}: {e}")
            return []
        except (KeyError, ValueError) as e:
            self.logger.error(f"Error parsing response from {self.company.name}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error fetching jobs from {self.company.name}: {e}")
            return []
