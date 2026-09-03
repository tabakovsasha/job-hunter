"""Tests for Yandex provider"""

from app.providers.yandex import YandexProvider
from app.models import Vacancy


def test_yandex_provider_basic():
    """Test Yandex provider basic functionality"""
    provider = YandexProvider()
    
    assert provider.name == 'yandex'
    assert 'yandex.ru' in provider.base_url


def test_yandex_provider_real_fetch():
    """Test fetching real data from Yandex (smoke test)"""
    provider = YandexProvider()
    
    try:
        vacancies = provider.get_vacancies('presale')
        
        print(f"Yandex Provider found {len(vacancies)} vacancies")
        
        # Should return a list
        assert isinstance(vacancies, list)
        
        # Check vacancy structure if any found
        if vacancies:
            vacancy = vacancies[0]
            assert isinstance(vacancy, Vacancy)
            assert vacancy.source == 'yandex'
            assert vacancy.external_id
            assert vacancy.title
            assert vacancy.url
            assert 'yandex.ru' in vacancy.url
            assert vacancy.company == 'Яндекс'
            
            print(f"Sample vacancy:")
            print(f"  ID: {vacancy.external_id}")
            print(f"  Title: {vacancy.title[:50]}...")
            print(f"  URL: {vacancy.url}")
            print(f"  Location: {vacancy.location}")
            print(f"  Company: {vacancy.company}")
    except Exception as e:
        print(f"Yandex Provider test failed: {e}")
        raise


if __name__ == '__main__':
    print("Testing Yandex Provider...")
    test_yandex_provider_basic()
    print("✓ test_yandex_provider_basic")
    test_yandex_provider_real_fetch()
    print("✓ test_yandex_provider_real_fetch")
    print("\nYandex Provider tests passed!")
