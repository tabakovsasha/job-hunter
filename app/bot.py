"""Telegram bot for manual vacancy checks via /update command"""

import logging
import time
import requests
from typing import Optional, Dict, Any

from app.storage import VacancyStorage
from app.telegram import TelegramNotifier
from app.monitor import run_check, CheckResult
from app.locking import check_lock, LockHeldError
from app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, HTTP_TIMEOUT

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot with long polling"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_base = f"https://api.telegram.org/bot{bot_token}"
        self.offset = 0
    
    def get_updates(self, timeout: int = 50) -> list[Dict[str, Any]]:
        """
        Get updates from Telegram using long polling.
        
        Args:
            timeout: Long polling timeout in seconds
        
        Returns:
            List of updates
        """
        try:
            url = f"{self.api_base}/getUpdates"
            params = {
                'offset': self.offset,
                'timeout': timeout
            }
            
            # HTTP timeout should be slightly longer than polling timeout
            response = requests.get(url, params=params, timeout=timeout + 10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                updates = result.get('result', [])
                if updates:
                    logger.debug(f"Received {len(updates)} updates")
                return updates
            else:
                logger.error(f"getUpdates returned ok=false: {result}")
                return []
                
        except requests.Timeout:
            # Long polling timeout is normal
            logger.debug("Long polling timeout (normal)")
            return []
        except Exception as e:
            logger.error(f"Failed to get updates: {e}")
            return []
    
    def send_message(self, chat_id: str, text: str) -> bool:
        """Send message to chat"""
        try:
            url = f"{self.api_base}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': text
            }
            
            response = requests.post(url, json=payload, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            
            result = response.json()
            return result.get('ok', False)
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    def is_authorized(self, chat_id: str) -> bool:
        """Check if chat_id is authorized"""
        return str(chat_id) == str(self.chat_id)
    
    def format_check_result(self, result: CheckResult) -> str:
        """Format check result as message"""
        if result.has_errors:
            lines = ["⚠️ Проверка завершена с ошибками", ""]
        else:
            lines = ["✅ Проверка завершена", ""]
        
        # Provider results
        for provider_name, provider_result in result.providers.items():
            if provider_result.success:
                lines.append(f"{provider_name.upper()}: {provider_result.total} вакансий")
            else:
                lines.append(f"{provider_name.upper()}: ошибка получения данных")
        
        lines.append("")
        
        # New vacancies count
        if result.new_found > 0:
            lines.append(f"🆕 Новых вакансий: {result.new_found}")
        else:
            lines.append(f"Новых вакансий: 0")
        
        return "\n".join(lines)
    
    def send_all_vacancies(self, storage: VacancyStorage):
        """Send list of all known vacancies"""
        try:
            stats = storage.get_stats()
            
            if stats['total_vacancies'] == 0:
                self.send_message(self.chat_id, "📭 Нет сохранённых вакансий")
                return
            
            # Group by source
            vacancies_by_source = {}
            for key, vacancy_data in storage.state['vacancies'].items():
                source = vacancy_data.get('source', 'Unknown')
                if source not in vacancies_by_source:
                    vacancies_by_source[source] = []
                vacancies_by_source[source].append(vacancy_data)
            
            # Send header
            header = f"📋 Все известные вакансии: {stats['total_vacancies']}\n"
            self.send_message(self.chat_id, header)
            
            # Send vacancies by source
            for source, vacancies in vacancies_by_source.items():
                source_header = f"\n🔹 {source.upper()}: {len(vacancies)} вакансий\n"
                self.send_message(self.chat_id, source_header)
                
                for vacancy_data in vacancies:
                    msg_lines = [vacancy_data.get('title', 'N/A')]
                    if vacancy_data.get('location'):
                        msg_lines.append(f"📍 {vacancy_data['location']}")
                    if vacancy_data.get('company'):
                        msg_lines.append(f"🏢 {vacancy_data['company']}")
                    msg_lines.append(vacancy_data.get('url', ''))
                    
                    self.send_message(self.chat_id, "\n".join(msg_lines))
                    
        except Exception as e:
            logger.error(f"Failed to send all vacancies: {e}", exc_info=True)

    
    def handle_update_command(self, chat_id: str):
        """Handle /update command"""
        logger.info(f"Processing /update command from chat {chat_id}")
        
        # Check authorization
        if not self.is_authorized(chat_id):
            logger.warning(f"Unauthorized /update attempt from chat {chat_id}")
            return
        
        # Send "checking" message
        self.send_message(chat_id, "🔄 Проверяю вакансии…")
        
        # Initialize components
        storage = VacancyStorage()
        notifier = TelegramNotifier()
        
        # Try to run check with lock
        try:
            with check_lock(non_blocking=True):
                result = run_check(storage, notifier)
                
                # Send summary
                summary = self.format_check_result(result)
                self.send_message(chat_id, summary)
                
                logger.info(f"/update completed: {result.new_found} new vacancies")
                
        except LockHeldError:
            logger.info("Check already in progress")
            self.send_message(chat_id, "⏳ Проверка уже выполняется. Попробуйте немного позже.")
        
        except Exception as e:
            logger.error(f"Failed to run check: {e}", exc_info=True)
            self.send_message(chat_id, "❌ Ошибка при проверке вакансий. Подробности в логах.")
    
    def handle_start_command(self, chat_id: str):
        """Handle /start command"""
        if not self.is_authorized(chat_id):
            return
        
        message = (
            "👋 Job Hunter\n\n"
            "Я слежу за новыми вакансиями.\n\n"
            "Доступные команды:\n"
            "/update — проверить вакансии сейчас\n"
            "/list — показать все известные вакансии"
        )
        self.send_message(chat_id, message)
    
    def handle_list_command(self, chat_id: str):
        """Handle /list command"""
        logger.info(f"Processing /list command from chat {chat_id}")
        
        # Check authorization
        if not self.is_authorized(chat_id):
            logger.warning(f"Unauthorized /list attempt from chat {chat_id}")
            return
        
        # Load storage and send all vacancies
        storage = VacancyStorage()
        self.send_all_vacancies(storage)

    
    def process_update(self, update: Dict[str, Any]):
        """Process single update"""
        try:
            update_id = update.get('update_id')
            message = update.get('message')
            
            logger.debug(f"Processing update {update_id}")
            
            if not message:
                logger.debug(f"Update {update_id} has no message")
                return
            
            chat_id = str(message.get('chat', {}).get('id', ''))
            text = message.get('text', '').strip()
            
            logger.debug(f"Message from chat {chat_id}: {text}")
            
            if not text.startswith('/'):
                logger.debug(f"Not a command: {text}")
                return
            
            # Remove bot username from command (e.g., /update@botname -> /update)
            command = text.split()[0].split('@')[0]
            
            logger.info(f"Processing command {command} from chat {chat_id}")
            
            # Handle commands
            if command == '/update':
                self.handle_update_command(chat_id)
            elif command == '/start':
                self.handle_start_command(chat_id)
            elif command == '/list':
                self.handle_list_command(chat_id)
            else:
                logger.debug(f"Unknown command: {command}")

            
            # Update offset
            if update_id:
                self.offset = max(self.offset, update_id + 1)
                
        except Exception as e:
            logger.error(f"Error processing update: {e}", exc_info=True)

    
    def run(self):
        """Run bot with long polling"""
        logger.info("Starting Telegram bot...")
        logger.info(f"Chat ID: {self.chat_id}")
        
        while True:
            try:
                updates = self.get_updates()
                
                for update in updates:
                    self.process_update(update)
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in bot loop: {e}", exc_info=True)
                time.sleep(5)  # Wait before retry


def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Bot entry point"""
    setup_logging()
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not configured in .env")
        return 1
    
    if not TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_CHAT_ID not configured in .env")
        return 1
    
    bot = TelegramBot(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    bot.run()
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

