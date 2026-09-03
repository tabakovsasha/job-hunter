"""Tests for VK provider"""

from app.providers.vk import VKProvider
from app.models import Vacancy


def test_vk_provider_basic():
    """Test VK provider basic functionality"""
    provider = VKProvider()
    
    assert provider.name == 'vk'
    assert 'team.vk.company' in provider.base_url


def test_vk_provider_real_fetch():
    """Test fetching real data from VK (smoke test)"""
    provider = VKProvider()
    
    try:
        vacancies = provider.get_vacancies('presale')
        
        print(f"VK Provider found {len(vacancies)} vacancies")
        
        # Should return a list
        assert isinstance(vacancies, list)
        
        # Check vacancy structure if any found
        if vacancies:
            vacancy = vacancies[0]
            assert isinstance(vacancy, Vacancy)
            assert vacancy.source == 'vk'
            assert vacancy.external_id
            assert vacancy.title
            assert vacancy.url
            assert 'team.vk.company' in vacancy.url
            
            print(f"Sample vacancy:")
            print(f"  ID: {vacancy.external_id}")
            print(f"  Title: {vacancy.title[:50]}...")
            print(f"  URL: {vacancy.url}")
            print(f"  Location: {vacancy.location}")
            print(f"  Company: {vacancy.company}")
    except Exception as e:
        print(f"VK Provider test failed: {e}")
        raise


if __name__ == '__main__':
    print("Testing VK Provider...")
    test_vk_provider_basic()
    print("✓ test_vk_provider_basic")
    test_vk_provider_real_fetch()
    print("✓ test_vk_provider_real_fetch")
    print("\nVK Provider tests passed!")
