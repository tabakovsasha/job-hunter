"""Base provider interface"""

from abc import ABC, abstractmethod
from typing import Protocol
from app.models import Vacancy


class VacancyProvider(Protocol):
    """Protocol for vacancy providers"""
    
    name: str
    
    def get_vacancies(self, query: str) -> list[Vacancy]:
        """
        Fetch vacancies matching the query.
        
        Args:
            query: Search query string
            
        Returns:
            List of Vacancy objects
            
        Raises:
            Exception: If fetching fails
        """
        ...
