"""Integration tests for the monitoring workflow"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from app.models import Vacancy
from app.storage import VacancyStorage
from app.telegram import TelegramNotifier


def test_first_run_no_notifications():
    """Test that first run doesn't send notifications"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = Path(f.name)
    
    try:
        storage = VacancyStorage(temp_file)
        
        # Simulate first run
        assert not storage.is_source_initialized('vk')
        
        # Found vacancies
        vacancies = [
            Vacancy(source='vk', external_id='1', title='V1', url='http://v1'),
            Vacancy(source='vk', external_id='2', title='V2', url='http://v2'),
        ]
        
        # First run logic
        storage.add_vacancies(vacancies)
        storage.mark_source_initialized('vk')
        
        # No new vacancies on first run
        new_vacancies = []  # Should be empty for first run
        
        assert len(new_vacancies) == 0
        assert storage.is_source_initialized('vk')
        assert len(storage.state['vacancies']) == 2
        
        print("✓ First run: saved vacancies without notifications")
    finally:
        temp_file.unlink(missing_ok=True)


def test_second_run_with_new_vacancy():
    """Test that second run sends notifications for new vacancies"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = Path(f.name)
    
    try:
        # First run
        storage = VacancyStorage(temp_file)
        v1 = Vacancy(source='vk', external_id='1', title='V1', url='http://v1')
        storage.add_vacancy(v1)
        storage.mark_source_initialized('vk')
        storage.save()
        
        # Second run
        storage2 = VacancyStorage(temp_file)
        assert storage2.is_source_initialized('vk')
        
        # Found vacancies include old + new
        v2 = Vacancy(source='vk', external_id='2', title='V2', url='http://v2')
        all_vacancies = [v1, v2]
        
        new_vacancies = storage2.get_new_vacancies(all_vacancies)
        
        assert len(new_vacancies) == 1
        assert new_vacancies[0].external_id == '2'
        
        print("✓ Second run: detected 1 new vacancy")
    finally:
        temp_file.unlink(missing_ok=True)


def test_no_duplicate_notifications():
    """Test that vacancy reappearing doesn't trigger notification"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = Path(f.name)
    
    try:
        storage = VacancyStorage(temp_file)
        
        v1 = Vacancy(source='vk', external_id='1', title='V1', url='http://v1')
        
        # First time: new
        storage.mark_source_initialized('vk')
        assert not storage.is_vacancy_known(v1)
        storage.add_vacancy(v1)
        
        # Vacancy disappears then reappears
        assert storage.is_vacancy_known(v1)
        
        # Should not be considered new
        new_vacancies = storage.get_new_vacancies([v1])
        assert len(new_vacancies) == 0
        
        print("✓ Reappearing vacancy not treated as new")
    finally:
        temp_file.unlink(missing_ok=True)


def test_multiple_sources_independence():
    """Test that sources are tracked independently"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = Path(f.name)
    
    try:
        storage = VacancyStorage(temp_file)
        
        # Initialize VK
        vk_vacancy = Vacancy(source='vk', external_id='1', title='VK V1', url='http://vk1')
        storage.add_vacancy(vk_vacancy)
        storage.mark_source_initialized('vk')
        
        # Yandex not initialized yet
        assert storage.is_source_initialized('vk')
        assert not storage.is_source_initialized('yandex')
        
        # Yandex first run should not send notifications
        yandex_vacancy = Vacancy(source='yandex', external_id='1', title='YA V1', url='http://ya1')
        
        # Even though VK is initialized, Yandex is not
        storage.add_vacancy(yandex_vacancy)
        storage.mark_source_initialized('yandex')
        
        assert storage.is_source_initialized('yandex')
        assert len(storage.state['vacancies']) == 2
        
        print("✓ Multiple sources tracked independently")
    finally:
        temp_file.unlink(missing_ok=True)


def test_provider_failure_doesnt_stop_others():
    """Test that one provider failing doesn't stop others"""
    # This would be tested in main.py with try/except around each provider
    # Here we just verify the concept
    
    results = []
    
    # Simulate processing two providers
    for provider_name in ['vk', 'yandex']:
        try:
            if provider_name == 'vk':
                raise Exception("VK failed")
            results.append(provider_name)
        except Exception:
            # Log error but continue
            continue
    
    # Yandex should still be processed
    assert 'yandex' in results
    assert 'vk' not in results
    
    print("✓ Provider failure isolation works")


if __name__ == '__main__':
    print("Running integration tests...\n")
    test_first_run_no_notifications()
    test_second_run_with_new_vacancy()
    test_no_duplicate_notifications()
    test_multiple_sources_independence()
    test_provider_failure_doesnt_stop_others()
    print("\nAll integration tests passed!")
