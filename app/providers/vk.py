"""VK Team vacancy provider"""

import re
import logging
import requests
from bs4 import BeautifulSoup
from typing import Optional

from app.models import Vacancy
from app.config import HTTP_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)


class VKProvider:
    """VK Team careers provider"""
    
    name = "vk"
    base_url = "https://team.vk.company"
    
    def get_vacancies(self, query: str) -> list[Vacancy]:
        """
        Fetch vacancies from VK Team.
        
        Args:
            query: Search query string
            
        Returns:
            List of Vacancy objects
        """
        url = f"{self.base_url}/vacancy/?search={query}"
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        logger.info(f"[VK] Fetching vacancies for query: {query}")
        logger.debug(f"[VK] URL: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            vacancy_links = soup.find_all('a', href=lambda x: x and '/vacancy/' in x and x != '/vacancy/')
            
            vacancies = []
            for link in vacancy_links:
                href = link.get('href')
                if '/vacancy/' not in href or href == '/vacancy/':
                    continue
                
                # Extract ID from URL
                match = re.search(r'/vacancy/(\d+)/', href)
                if not match:
                    continue
                
                vac_id = match.group(1)
                title = link.get_text(strip=True)
                
                # Extract location and company from parent element
                location = None
                company = None
                parent = link.find_parent(['div', 'article', 'li'])
                
                if parent:
                    text = parent.get_text()
                    if 'Москва' in text:
                        location = 'Москва'
                    elif 'Санкт-Петербург' in text:
                        location = 'Санкт-Петербург'
                    elif 'Алма-Ата' in text:
                        location = 'Алма-Ата'
                    
                    if 'VK Tech' in text:
                        company = 'VK Tech'
                    elif 'VK' in text:
                        company = 'VK'
                
                vacancy = Vacancy(
                    source=self.name,
                    external_id=vac_id,
                    title=title,
                    url=f"{self.base_url}{href}",
                    location=location,
                    company=company
                )
                vacancies.append(vacancy)
            
            logger.info(f"[VK] Found {len(vacancies)} vacancies")
            return vacancies
            
        except requests.RequestException as e:
            logger.error(f"[VK] Failed to fetch vacancies: {e}")
            raise
        except Exception as e:
            logger.error(f"[VK] Error parsing vacancies: {e}")
            raise
