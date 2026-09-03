"""State storage management"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.models import Vacancy
from app.config import STATE_FILE

logger = logging.getLogger(__name__)


class VacancyStorage:
    """Manages vacancy state persistence"""
    
    def __init__(self, state_file: Path = STATE_FILE):
        self.state_file = state_file
        self.state = self._load_state()
    
    def _load_state(self) -> dict:
        """Load state from JSON file"""
        if not self.state_file.exists():
            logger.info(f"State file not found, creating new state")
            return {
                'sources': {},
                'vacancies': {}
            }
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                logger.info(f"Loaded state with {len(state.get('vacancies', {}))} vacancies")
                return state
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse state file: {e}")
            # Backup corrupted file
            backup_file = self.state_file.with_suffix('.json.backup')
            self.state_file.rename(backup_file)
            logger.warning(f"Corrupted state file backed up to {backup_file}")
            return {'sources': {}, 'vacancies': {}}
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            return {'sources': {}, 'vacancies': {}}
    
    def _save_state(self) -> None:
        """Save state to JSON file atomically"""
        try:
            # Write to temporary file first
            temp_file = self.state_file.with_suffix('.json.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
            
            # Atomic replace
            temp_file.replace(self.state_file)
            logger.debug(f"State saved to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            raise
    
    def is_source_initialized(self, source: str) -> bool:
        """Check if source has been initialized"""
        return self.state['sources'].get(source, {}).get('initialized', False)
    
    def mark_source_initialized(self, source: str) -> None:
        """Mark source as initialized"""
        if source not in self.state['sources']:
            self.state['sources'][source] = {}
        self.state['sources'][source]['initialized'] = True
        logger.info(f"Source '{source}' marked as initialized")
    
    def is_vacancy_known(self, vacancy: Vacancy) -> bool:
        """Check if vacancy is already known"""
        key = vacancy.get_unique_key()
        return key in self.state['vacancies']
    
    def add_vacancy(self, vacancy: Vacancy, first_seen: Optional[datetime] = None) -> None:
        """Add vacancy to state"""
        if first_seen is None:
            first_seen = datetime.now(timezone.utc)
        
        key = vacancy.get_unique_key()
        self.state['vacancies'][key] = {
            'source': vacancy.source,
            'external_id': vacancy.external_id,
            'title': vacancy.title,
            'url': vacancy.url,
            'location': vacancy.location,
            'company': vacancy.company,
            'first_seen': first_seen.isoformat()
        }
    
    def add_vacancies(self, vacancies: list[Vacancy]) -> None:
        """Add multiple vacancies to state"""
        now = datetime.now(timezone.utc)
        for vacancy in vacancies:
            if not self.is_vacancy_known(vacancy):
                self.add_vacancy(vacancy, now)
    
    def get_new_vacancies(self, vacancies: list[Vacancy]) -> list[Vacancy]:
        """Filter vacancies to only new ones"""
        return [v for v in vacancies if not self.is_vacancy_known(v)]
    
    def save(self) -> None:
        """Save current state to disk"""
        self._save_state()
    
    def get_stats(self) -> dict:
        """Get storage statistics"""
        return {
            'total_vacancies': len(self.state['vacancies']),
            'sources': list(self.state['sources'].keys()),
            'initialized_sources': [
                source for source, data in self.state['sources'].items()
                if data.get('initialized', False)
            ]
        }
