"""Shared vacancy monitoring logic"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Optional

from app.models import Vacancy
from app.storage import VacancyStorage
from app.telegram import TelegramNotifier
from app.providers.vk import VKProvider
from app.providers.yandex import YandexProvider
from app.config import ENABLE_VK, ENABLE_YANDEX, SEARCH_QUERIES

logger = logging.getLogger(__name__)


@dataclass
class ProviderCheckResult:
    """Result of checking a single provider"""
    source: str
    total: int
    new: int
    success: bool
    error: Optional[str] = None


@dataclass
class CheckResult:
    """Result of complete vacancy check"""
    total_found: int
    new_found: int
    providers: Dict[str, ProviderCheckResult]
    has_errors: bool


def get_enabled_providers() -> List:
    """Get list of enabled providers"""
    providers = []
    
    if ENABLE_VK:
        providers.append(VKProvider())
    
    if ENABLE_YANDEX:
        providers.append(YandexProvider())
    
    return providers


def process_provider(
    provider,
    query: str,
    storage: VacancyStorage,
    notifier: TelegramNotifier
) -> tuple[int, int]:
    """
    Process a single provider.
    
    Returns:
        Tuple of (total_found, new_count)
    """
    try:
        # Fetch vacancies
        vacancies = provider.get_vacancies(query)
        
        # Check if this is first run for this source
        is_initial_scan = not storage.is_source_initialized(provider.name)
        
        if is_initial_scan:
            logger.info(
                f"[{provider.name.upper()}] Initial scan, "
                f"saving {len(vacancies)} vacancies without notifications"
            )
            storage.add_vacancies(vacancies)
            storage.mark_source_initialized(provider.name)
            return len(vacancies), 0
        
        # Filter to new vacancies only
        new_vacancies = storage.get_new_vacancies(vacancies)
        
        logger.info(f"[{provider.name.upper()}] New vacancies: {len(new_vacancies)}")
        
        # Send notifications for new vacancies
        notification_failures = []
        for vacancy in new_vacancies:
            success = notifier.send_vacancy_notification(vacancy)
            if not success:
                notification_failures.append(vacancy)
        
        # Only mark vacancies as known if notification succeeded
        if notification_failures:
            logger.warning(
                f"[{provider.name.upper()}] Failed to send "
                f"{len(notification_failures)} notifications, will retry next time"
            )
            successfully_notified = [v for v in new_vacancies if v not in notification_failures]
            storage.add_vacancies(successfully_notified)
        else:
            storage.add_vacancies(new_vacancies)
        
        return len(vacancies), len(new_vacancies)
        
    except Exception as e:
        logger.error(f"[{provider.name.upper()}] Failed to process: {e}", exc_info=True)
        raise


def run_check(storage: VacancyStorage, notifier: TelegramNotifier) -> CheckResult:
    """
    Run complete vacancy check across all enabled providers.
    
    This is the main business logic that can be called from:
    - CLI (app.main)
    - Telegram bot (app.bot)
    
    Args:
        storage: VacancyStorage instance
        notifier: TelegramNotifier instance
    
    Returns:
        CheckResult with aggregated results
    """
    providers = get_enabled_providers()
    
    if not providers:
        logger.error("No providers enabled")
        raise ValueError("No providers enabled. Set ENABLE_VK=true or ENABLE_YANDEX=true")
    
    if not SEARCH_QUERIES:
        logger.error("No search queries configured")
        raise ValueError("No search queries configured. Set SEARCH_QUERIES in .env")
    
    logger.info(f"Enabled providers: {[p.name for p in providers]}")
    logger.info(f"Search queries: {SEARCH_QUERIES}")
    
    # Track results per provider
    provider_results: Dict[str, ProviderCheckResult] = {}
    total_found = 0
    total_new = 0
    has_errors = False
    
    # Process each provider
    for provider in providers:
        provider_total = 0
        provider_new = 0
        provider_error = None
        provider_success = True
        
        try:
            for query in SEARCH_QUERIES:
                found, new = process_provider(provider, query, storage, notifier)
                provider_total += found
                provider_new += new
        
        except Exception as e:
            provider_success = False
            provider_error = str(e)
            has_errors = True
            logger.error(f"[{provider.name.upper()}] Provider failed: {e}")
        
        # Record provider result
        provider_results[provider.name] = ProviderCheckResult(
            source=provider.name,
            total=provider_total,
            new=provider_new,
            success=provider_success,
            error=provider_error
        )
        
        if provider_success:
            total_found += provider_total
            total_new += provider_new
    
    # Save state
    try:
        storage.save()
        logger.info("State saved successfully")
    except Exception as e:
        logger.error(f"Failed to save state: {e}")
        has_errors = True
        raise
    
    # Build result
    result = CheckResult(
        total_found=total_found,
        new_found=total_new,
        providers=provider_results,
        has_errors=has_errors
    )
    
    # Summary
    stats = storage.get_stats()
    logger.info("Vacancy check completed")
    logger.info(f"Total vacancies found this run: {total_found}")
    logger.info(f"New vacancies: {total_new}")
    logger.info(f"Total vacancies in database: {stats['total_vacancies']}")
    
    if total_new > 0:
        logger.info(f"Sent {total_new} Telegram notifications")
    
    return result

