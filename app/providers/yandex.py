"""Yandex Careers vacancy provider"""

import re
import logging
import requests
from bs4 import BeautifulSoup

from app.models import Vacancy
from app.config import HTTP_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)


class YandexProvider:
    """Yandex Careers provider"""
    
    name = "yandex"
    base_url = "https://yandex.ru"
    
    def get_vacancies(self, query: str) -> list[Vacancy]:
        """
        Fetch vacancies from Yandex Careers.
        
        Args:
            query: Search query string
            
        Returns:
            List of Vacancy objects
        """
        url = f"{self.base_url}/jobs/vacancies?from=cp_fastfilters&text={query}"
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru,en;q=0.9',
            'Referer': f'{self.base_url}/jobs/'
        }
        
        logger.info(f"[YANDEX] Fetching vacancies for query: {query}")
        logger.debug(f"[YANDEX] URL: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find vacancy links with VacancySnippet class
            vacancy_links = soup.find_all('a', class_=re.compile('VacancySnippet.*titleLink'))
            
            vacancies = []
            for link in vacancy_links:
                href = link.get('href')
                if not href:
                    continue
                
                # Extract ID from URL
                match = re.search(r'/jobs/vacancies/[^/]+-(\d+)', href)
                if not match:
                    # Try alternative pattern
                    match = re.search(r'/jobs/vacancies/(\d+)', href)
                    if not match:
                        # Use slug as ID if numeric ID not found
                        slug_match = re.search(r'/jobs/vacancies/([^/?]+)', href)
                        if slug_match:
                            vac_id = slug_match.group(1).split('?')[0]
                        else:
                            continue
                    else:
                        vac_id = match.group(1)
                else:
                    vac_id = match.group(1)
                
                title = link.get_text(strip=True)
                
                # Extract location from parent element
                location = None
                parent = link.find_parent(['div', 'article', 'li'])
                
                if parent:
                    text = parent.get_text()
                    cities = ['Москва', 'Санкт-Петербург', 'Казань', 'Екатеринбург', 'Нижний Новгород']
                    for city in cities:
                        if city in text:
                            location = city
                            break
                
                # Make URL absolute
                if href.startswith('/'):
                    full_url = f"{self.base_url}{href}"
                else:
                    full_url = href
                
                vacancy = Vacancy(
                    source=self.name,
                    external_id=vac_id,
                    title=title,
                    url=full_url,
                    location=location,
                    company='Яндекс'
                )
                vacancies.append(vacancy)
            
            logger.info(f"[YANDEX] Found {len(vacancies)} vacancies")
            return vacancies
            
        except requests.RequestException as e:
            logger.error(f"[YANDEX] Failed to fetch vacancies: {e}")
            raise
        except Exception as e:
            logger.error(f"[YANDEX] Error parsing vacancies: {e}")
            raise
