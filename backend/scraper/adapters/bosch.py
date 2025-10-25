"""
Bosch adapter for fetching job postings.

Bosch may require HTML scraping if no public API is available.
"""

import requests
from bs4 import BeautifulSoup
from typing import List
from scraper.base import BaseAdapter, RawJobPosting


class BoschAdapter(BaseAdapter):
    """Adapter for Bosch careers page."""
    
    def fetch_jobs(self) -> List[RawJobPosting]:
        """
        Fetch jobs from Bosch careers page.
        
        Returns:
            List of RawJobPosting objects, empty list on failure
        """
        try:
            # Fetch careers page
            response = requests.get(
                self.company.careers_url,
                timeout=20,
                headers={'User-Agent': 'JobRoleMatcher/1.0'}
            )
            response.raise_for_status()
            
            # Try JSON API first (many companies have hidden JSON endpoints)
            if 'application/json' in response.headers.get('Content-Type', ''):
                return self._parse_json_response(response.json())
            else:
                return self._parse_html_response(response.text)
            
        except requests.exceptions.Timeout:
            self.logger.error(f"Timeout fetching jobs from {self.company.name}")
            return []
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error fetching jobs from {self.company.name}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error fetching jobs from {self.company.name}: {e}")
            return []
    
    def _parse_json_response(self, data) -> List[RawJobPosting]:
        """Parse JSON API response."""
        jobs = []
        
        # Handle different JSON structures
        job_listings = data.get('jobs', []) if isinstance(data, dict) else data
        
        for job_data in job_listings:
            external_id = str(job_data.get('id') or job_data.get('jobId', ''))
            title = job_data.get('title', '')
            location = job_data.get('location', '')
            description = job_data.get('description', '') or job_data.get('summary', '')
            url = job_data.get('url', '') or job_data.get('link', '')
            department = job_data.get('department')
            
            if not all([external_id, title, location, description, url]):
                continue
            
            # Check if description is truncated
            partial_description = len(description) < 100
            
            jobs.append(RawJobPosting(
                external_id=external_id,
                title=title,
                location=location,
                description=description,
                url=url,
                partial_description=partial_description,
                department=department
            ))
        
        self.logger.info(f"Fetched {len(jobs)} jobs from Bosch (JSON)")
        return jobs
    
    def _parse_html_response(self, html: str) -> List[RawJobPosting]:
        """Parse HTML careers page."""
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []
        
        # This is a template - actual selectors depend on Bosch's HTML structure
        # Common patterns: job listings in <div class="job-item"> or <article>
        job_elements = soup.find_all(['div', 'article'], class_=lambda x: x and 'job' in x.lower())
        
        for job_elem in job_elements:
            try:
                # Extract job details using common patterns
                title_elem = job_elem.find(['h2', 'h3', 'a'], class_=lambda x: x and 'title' in x.lower())
                title = title_elem.get_text(strip=True) if title_elem else ''
                
                location_elem = job_elem.find(class_=lambda x: x and 'location' in x.lower())
                location = location_elem.get_text(strip=True) if location_elem else ''
                
                # Try to find job link
                link_elem = job_elem.find('a', href=True)
                url = link_elem['href'] if link_elem else ''
                if url and not url.startswith('http'):
                    # Make absolute URL
                    base_url = '/'.join(self.company.careers_url.split('/')[:3])
                    url = base_url + url
                
                # Extract ID from URL or data attribute
                external_id = job_elem.get('data-job-id', '')
                if not external_id and url:
                    # Try to extract from URL
                    parts = url.split('/')
                    external_id = parts[-1] if parts else ''
                
                # Description often truncated in listings
                desc_elem = job_elem.find(class_=lambda x: x and ('description' in x.lower() or 'summary' in x.lower()))
                description = desc_elem.get_text(strip=True) if desc_elem else title
                
                if not all([external_id, title, location, url]):
                    continue
                
                jobs.append(RawJobPosting(
                    external_id=external_id,
                    title=title,
                    location=location,
                    description=description,
                    url=url,
                    partial_description=True,  # HTML scraping usually gets summaries only
                    department=None
                ))
                
            except Exception as e:
                self.logger.warning(f"Error parsing job element: {e}")
                continue
        
        self.logger.info(f"Fetched {len(jobs)} jobs from Bosch (HTML)")
        return jobs
