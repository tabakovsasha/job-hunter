"""Data models for vacancy tracking"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional


@dataclass
class Vacancy:
    """Unified vacancy model across all sources"""
    source: str
    external_id: str
    title: str
    url: str
    location: Optional[str] = None
    company: Optional[str] = None
    published_at: Optional[datetime] = None
    
    def get_unique_key(self) -> str:
        """Get unique identifier for this vacancy"""
        return f"{self.source}:{self.external_id}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage"""
        data = asdict(self)
        if self.published_at:
            data['published_at'] = self.published_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Vacancy':
        """Create Vacancy from dictionary"""
        if data.get('published_at') and isinstance(data['published_at'], str):
            data['published_at'] = datetime.fromisoformat(data['published_at'])
        return cls(**data)
