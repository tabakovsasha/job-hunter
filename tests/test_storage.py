"""Tests for vacancy storage"""

import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from app.models import Vacancy
from app.storage import VacancyStorage


def test_initial_state():
    """Test that new storage starts empty"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = Path(f.name)
    
    try:
        storage = VacancyStorage(temp_file)
        assert storage.state['sources'] == {}
        assert storage.state['vacancies'] == {}
    finally:
        temp_file.unlink(missing_ok=True)


def test_source_initialization():
    """Test source initialization tracking"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = Path(f.name)
    
    try:
        storage = VacancyStorage(temp_file)
        
        # Initially not initialized
        assert not storage.is_source_initialized('vk')
        
        # Mark as initialized
        storage.mark_source_initialized('vk')
        assert storage.is_source_initialized('vk')
        
        # Save and reload
        storage.save()
        storage2 = VacancyStorage(temp_file)
        assert storage2.is_source_initialized('vk')
    finally:
        temp_file.unlink(missing_ok=True)


def test_vacancy_tracking():
    """Test vacancy add and check"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = Path(f.name)
    
    try:
        storage = VacancyStorage(temp_file)
        
        vacancy = Vacancy(
            source='vk',
            external_id='12345',
            title='Test Vacancy',
            url='https://example.com/vacancy/12345',
            location='Москва',
            company='Test Company'
        )
        
        # Initially unknown
        assert not storage.is_vacancy_known(vacancy)
        
        # Add vacancy
        storage.add_vacancy(vacancy)
        assert storage.is_vacancy_known(vacancy)
        
        # Check key
        key = vacancy.get_unique_key()
        assert key == 'vk:12345'
        assert key in storage.state['vacancies']
    finally:
        temp_file.unlink(missing_ok=True)


def test_new_vacancy_filtering():
    """Test filtering new vs known vacancies"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = Path(f.name)
    
    try:
        storage = VacancyStorage(temp_file)
        
        v1 = Vacancy(source='vk', external_id='1', title='V1', url='http://v1')
        v2 = Vacancy(source='vk', external_id='2', title='V2', url='http://v2')
        v3 = Vacancy(source='yandex', external_id='1', title='V3', url='http://v3')
        
        # Add v1
        storage.add_vacancy(v1)
        
        # Filter list
        all_vacancies = [v1, v2, v3]
        new_vacancies = storage.get_new_vacancies(all_vacancies)
        
        assert len(new_vacancies) == 2
        assert v1 not in new_vacancies
        assert v2 in new_vacancies
        assert v3 in new_vacancies
    finally:
        temp_file.unlink(missing_ok=True)


def test_unique_keys_different_sources():
    """Test that same ID from different sources are different"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = Path(f.name)
    
    try:
        storage = VacancyStorage(temp_file)
        
        v1 = Vacancy(source='vk', external_id='12345', title='VK Vacancy', url='http://vk')
        v2 = Vacancy(source='yandex', external_id='12345', title='Yandex Vacancy', url='http://ya')
        
        storage.add_vacancy(v1)
        
        # v2 should be new even though ID is same
        assert not storage.is_vacancy_known(v2)
        
        storage.add_vacancy(v2)
        assert storage.is_vacancy_known(v2)
        
        # Both should be in storage
        assert len(storage.state['vacancies']) == 2
    finally:
        temp_file.unlink(missing_ok=True)


def test_persistence():
    """Test that state persists across instances"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = Path(f.name)
    
    try:
        # First instance
        storage1 = VacancyStorage(temp_file)
        vacancy = Vacancy(source='vk', external_id='999', title='Persist Test', url='http://test')
        storage1.add_vacancy(vacancy)
        storage1.mark_source_initialized('vk')
        storage1.save()
        
        # Second instance
        storage2 = VacancyStorage(temp_file)
        assert storage2.is_vacancy_known(vacancy)
        assert storage2.is_source_initialized('vk')
        assert len(storage2.state['vacancies']) == 1
    finally:
        temp_file.unlink(missing_ok=True)


if __name__ == '__main__':
    print("Running storage tests...")
    test_initial_state()
    print("✓ test_initial_state")
    test_source_initialization()
    print("✓ test_source_initialization")
    test_vacancy_tracking()
    print("✓ test_vacancy_tracking")
    test_new_vacancy_filtering()
    print("✓ test_new_vacancy_filtering")
    test_unique_keys_different_sources()
    print("✓ test_unique_keys_different_sources")
    test_persistence()
    print("✓ test_persistence")
    print("\nAll tests passed!")
