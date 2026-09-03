"""Telegram notification sender"""

import logging
import requests
from typing import Optional

from app.models import Vacancy
from app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, HTTP_TIMEOUT

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends notifications to Telegram"""
    
    def __init__(self, bot_token: str = TELEGRAM_BOT_TOKEN, chat_id: str = TELEGRAM_CHAT_ID):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    def _format_vacancy_message(self, vacancy: Vacancy) -> str:
        """Format vacancy as Telegram message"""
        source_emoji = {
            'vk': '🔥 Новая вакансия VK',
            'yandex': '🔥 Новая вакансия Yandex'
        }
        
        header = source_emoji.get(vacancy.source, f'🔥 Новая вакансия {vacancy.source}')
        
        lines = [header, '', vacancy.title]
        
        if vacancy.location:
            lines.append(f'📍 {vacancy.location}')
        
        if vacancy.company:
            lines.append(f'🏢 {vacancy.company}')
        
        lines.append('')
        lines.append(vacancy.url)
        
        return '\n'.join(lines)
    
    def send_vacancy_notification(self, vacancy: Vacancy) -> bool:
        """
        Send notification about new vacancy.
        
        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not configured, skipping notification")
            return False
        
        message = self._format_vacancy_message(vacancy)
        
        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'disable_web_page_preview': False
            }
            
            response = requests.post(self.api_url, json=payload, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                logger.info(f"Telegram notification sent for vacancy {vacancy.get_unique_key()}")
                return True
            else:
                logger.error(f"Telegram API returned ok=false: {result}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
            return False
    
    def send_test_message(self, message: str = "🤖 Job Hunter is running!") -> bool:
        """
        Send test message to verify Telegram configuration.
        
        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self.bot_token or not self.chat_id:
            logger.error("Telegram credentials not configured")
            return False
        
        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message
            }
            
            response = requests.post(self.api_url, json=payload, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                logger.info("Test message sent successfully")
                return True
            else:
                logger.error(f"Telegram API returned ok=false: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send test message: {e}")
            return False
    
    def send_message(self, text: str, chat_id: Optional[str] = None) -> bool:
        """
        Send plain text message.
        
        Args:
            text: Message text
            chat_id: Optional chat ID (uses default if not specified)
        
        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self.bot_token:
            logger.warning("Telegram bot token not configured")
            return False
        
        target_chat_id = chat_id or self.chat_id
        if not target_chat_id:
            logger.warning("Telegram chat ID not configured")
            return False
        
        try:
            payload = {
                'chat_id': target_chat_id,
                'text': text
            }
            
            response = requests.post(self.api_url, json=payload, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                logger.debug(f"Message sent to chat {target_chat_id}")
                return True
            else:
                logger.error(f"Telegram API returned ok=false: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

