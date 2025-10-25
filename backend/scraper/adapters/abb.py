"""
ABB adapter for fetching job postings.

ABB adapter with support for both API and HTML scraping.
"""

import requests
from bs4 import BeautifulSoup
from typing import List
from scraper.base import BaseAdapter, RawJobPosting


class ABBAdapter(BaseAdapter):
    """Adapter for ABB careers system."""
    
    def fetch_jobs(self) -> List[RawJobPosting]:
        """
        Fetch jobs from ABB careers system.
        
        Returns:
            List of RawJobPosting objects, empty list on failure
        """
        try:
            # Attempt to fetch from careers URL
            response = requests.get(
                self.company.careers_url,
                timeout=20,
                headers={
                    'User-Agent': 'JobRoleMatcher/1.0',
                    'Accept': 'application/json, text/html'
                }
            )
            response.raise_for_status()
            
            # Detect response type and parse accordingly
            content_type = response.headers.get('Content-Type', '')
            
            if 'application/json' in content_type:
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
        
        try:
            # Handle various JSON structures
            if isinstance(data, dict):
                job_listings = (
                    data.get('jobs') or 
                    data.get('data') or 
                    data.get('results') or 
                    []
                )
            else:
                job_listings = data
            
            for job_data in job_listings:
                # Extract fields with fallbacks
                external_id = str(
                    job_data.get('id') or 
                    job_data.get('jobId') or 
                    job_data.get('requisitionId') or 
                    ''
                )
                
                title = job_data.get('title') or job_data.get('jobTitle') or ''
                
                location = (
                    job_data.get('location') or 
                    job_data.get('city') or 
                    job_data.get('country') or 
                    ''
                )
                
                description = (
                    job_data.get('description') or 
                    job_data.get('jobDescription') or 
                    job_data.get('summary') or 
                    ''
                )
                
                url = (
                    job_data.get('url') or 
                    job_data.get('link') or 
                    job_data.get('applyUrl') or 
                    ''
                )
                
                department = job_data.get('department') or job_data.get('division')
                
                # Validate required fields
                if not all([external_id, title, location, description, url]):
                    self.logger.warning(
                        f"Skipping job with missing fields: id={external_id}, title={title}"
                    )
                    continue
                
                # Detect partial descriptions
                partial_description = (
                    len(description) < 150 or 
                    'click to view' in description.lower() or
                    'read more' in description.lower()
                )
                
                jobs.append(RawJobPosting(
                    external_id=external_id,
                    title=title,
                    location=location,
                    description=description,
                    url=url,
                    partial_description=partial_description,
                    department=department
                ))
            
            self.logger.info(f"Fetched {len(jobs)} jobs from ABB (JSON)")
            return jobs
            
        except (KeyError, ValueError, TypeError) as e:
            self.logger.error(f"Error parsing JSON response from {self.company.name}: {e}")
            return []
    
    def _parse_html_response(self, html: str) -> List[RawJobPosting]:
        """Parse HTML careers page."""
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []
        
        try:
            # Look for common job listing patterns
            # Try multiple selectors as different companies use different structures
            job_elements = (
                soup.find_all('div', class_=lambda x: x and 'job' in x.lower()) or
                soup.find_all('article', class_=lambda x: x and 'job' in x.lower()) or
                soup.find_all('li', class_=lambda x: x and 'job' in x.lower())
            )
            
            for job_elem in job_elements:
                try:
                    # Extract title
                    title_elem = (
                        job_elem.find('h2') or 
                        job_elem.find('h3') or 
                        job_elem.find(class_=lambda x: x and 'title' in x.lower())
                    )
                    title = title_elem.get_text(strip=True) if title_elem else ''
                    
                    # Extract location
                    location_elem = job_elem.find(class_=lambda x: x and 'location' in x.lower())
                    location = location_elem.get_text(strip=True) if location_elem else 'Not specified'
                    
                    # Extract URL
                    link_elem = job_elem.find('a', href=True)
                    url = link_elem['href'] if link_elem else ''
                    
                    # Make URL absolute if needed
                    if url and not url.startswith('http'):
                        base_url = '/'.join(self.company.careers_url.split('/')[:3])
                        url = base_url + ('/' if not url.startswith('/') else '') + url
                    
                    # Extract or generate external ID
                    external_id = (
                        job_elem.get('data-job-id') or 
                        job_elem.get('data-id') or 
                        job_elem.get('id') or
                        ''
                    )
                    
                    if not external_id and url:
                        # Extract from URL
                        url_parts = [p for p in url.split('/') if p]
                        external_id = url_parts[-1] if url_parts else ''
                    
                    # Extract description/summary
                    desc_elem = job_elem.find(class_=lambda x: x and (
                        'description' in x.lower() or 
                        'summary' in x.lower() or
                        'excerpt' in x.lower()
                    ))
                    description = desc_elem.get_text(strip=True) if desc_elem else title
                    
                    # Validate required fields
                    if not all([external_id, title, url]):
                        self.logger.warning(f"Skipping job with missing fields: {title}")
                        continue
                    
                    jobs.append(RawJobPosting(
                        external_id=external_id,
                        title=title,
                        location=location,
                        description=description,
                        url=url,
                        partial_description=True,  # HTML scraping typically gets summaries only
                        department=None
                    ))
                    
                except Exception as e:
                    self.logger.warning(f"Error parsing job element: {e}")
                    continue
            
            self.logger.info(f"Fetched {len(jobs)} jobs from ABB (HTML)")
            return jobs
            
        except Exception as e:
            self.logger.error(f"Error parsing HTML response from {self.company.name}: {e}")
            return []
