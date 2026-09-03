"""Tests for Telegram bot and manual /update command"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json
from pathlib import Path

from app.bot import TelegramBot
from app.monitor import CheckResult, ProviderCheckResult
from app.locking import CheckLock, LockHeldError, check_lock


class TestCheckLock(unittest.TestCase):
    """Test inter-process locking"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.lock_file = Path(self.temp_dir) / "test.lock"
    
    def test_lock_acquire_release(self):
        """Test basic lock acquire and release"""
        lock = CheckLock(self.lock_file)
        
        # Acquire lock
        self.assertTrue(lock.acquire(non_blocking=True))
        
        # Release lock
        lock.release()
        
        # Should be able to acquire again
        self.assertTrue(lock.acquire(non_blocking=True))
        lock.release()
    
    def test_lock_concurrent_access(self):
        """Test that second lock fails when first is held"""
        lock1 = CheckLock(self.lock_file)
        lock2 = CheckLock(self.lock_file)
        
        # First lock acquires
        self.assertTrue(lock1.acquire(non_blocking=True))
        
        # Second lock should fail
        self.assertFalse(lock2.acquire(non_blocking=True))
        
        # Release first lock
        lock1.release()
        
        # Now second lock should succeed
        self.assertTrue(lock2.acquire(non_blocking=True))
        lock2.release()
    
    def test_lock_context_manager(self):
        """Test lock as context manager"""
        with check_lock(non_blocking=False) as lock:
            self.assertIsNotNone(lock)
            
            # Try to acquire another lock - should raise
            with self.assertRaises(LockHeldError):
                with check_lock(non_blocking=True):
                    pass


class TestTelegramBot(unittest.TestCase):
    """Test Telegram bot functionality"""
    
    def setUp(self):
        self.bot_token = "test_token"
        self.chat_id = "123456789"
        self.bot = TelegramBot(self.bot_token, self.chat_id)
    
    def test_is_authorized(self):
        """Test authorization check"""
        self.assertTrue(self.bot.is_authorized("123456789"))
        self.assertTrue(self.bot.is_authorized(123456789))
        self.assertFalse(self.bot.is_authorized("999999999"))
        self.assertFalse(self.bot.is_authorized(999999999))
    
    def test_format_check_result_success(self):
        """Test formatting successful check result"""
        result = CheckResult(
            total_found=5,
            new_found=2,
            providers={
                'vk': ProviderCheckResult('vk', 3, 1, True),
                'yandex': ProviderCheckResult('yandex', 2, 1, True)
            },
            has_errors=False
        )
        
        message = self.bot.format_check_result(result)
        
        self.assertIn("✅ Проверка завершена", message)
        self.assertIn("VK: 3 вакансий", message)
        self.assertIn("YANDEX: 2 вакансий", message)
        self.assertIn("🆕 Новых вакансий: 2", message)
    
    def test_format_check_result_with_errors(self):
        """Test formatting check result with provider errors"""
        result = CheckResult(
            total_found=2,
            new_found=0,
            providers={
                'vk': ProviderCheckResult('vk', 0, 0, False, "Connection timeout"),
                'yandex': ProviderCheckResult('yandex', 2, 0, True)
            },
            has_errors=True
        )
        
        message = self.bot.format_check_result(result)
        
        self.assertIn("⚠️ Проверка завершена с ошибками", message)
        self.assertIn("VK: ошибка получения данных", message)
        self.assertIn("YANDEX: 2 вакансий", message)
    
    def test_format_check_result_no_new_vacancies(self):
        """Test formatting result with no new vacancies"""
        result = CheckResult(
            total_found=5,
            new_found=0,
            providers={
                'vk': ProviderCheckResult('vk', 5, 0, True)
            },
            has_errors=False
        )
        
        message = self.bot.format_check_result(result)
        
        self.assertIn("Новых вакансий: 0", message)
        self.assertNotIn("🆕", message)
    
    @patch('app.bot.requests.post')
    def test_send_message_success(self, mock_post):
        """Test successful message sending"""
        mock_response = Mock()
        mock_response.json.return_value = {'ok': True}
        mock_post.return_value = mock_response
        
        result = self.bot.send_message(self.chat_id, "Test message")
        
        self.assertTrue(result)
        mock_post.assert_called_once()
    
    @patch('app.bot.requests.post')
    def test_send_message_failure(self, mock_post):
        """Test message sending failure"""
        mock_post.side_effect = Exception("Network error")
        
        result = self.bot.send_message(self.chat_id, "Test message")
        
        self.assertFalse(result)
    
    @patch('app.bot.requests.get')
    def test_get_updates(self, mock_get):
        """Test getting updates"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'ok': True,
            'result': [
                {'update_id': 1, 'message': {'text': '/start'}}
            ]
        }
        mock_get.return_value = mock_response
        
        updates = self.bot.get_updates()
        
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]['update_id'], 1)
    
    def test_process_update_offset(self):
        """Test that offset is updated correctly"""
        self.bot.offset = 0
        
        update = {
            'update_id': 5,
            'message': {
                'chat': {'id': 999},
                'text': '/unknown'
            }
        }
        
        self.bot.process_update(update)
        
        # Offset should be update_id + 1
        self.assertEqual(self.bot.offset, 6)


if __name__ == '__main__':
    unittest.main()

