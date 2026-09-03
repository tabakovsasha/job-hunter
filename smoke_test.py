#!/usr/bin/env python3
"""Smoke test for /update functionality"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.locking import CheckLock, check_lock, LockHeldError
from app.config import DATA_DIR

def test_lock():
    """Test file lock mechanism"""
    print("Testing file lock...")
    
    lock_file = DATA_DIR / "test_smoke.lock"
    
    # Test 1: Basic acquire/release
    lock1 = CheckLock(lock_file)
    assert lock1.acquire(non_blocking=True), "Failed to acquire lock"
    print("✓ Lock acquired")
    
    # Test 2: Second lock should fail
    lock2 = CheckLock(lock_file)
    assert not lock2.acquire(non_blocking=True), "Second lock should fail"
    print("✓ Second lock correctly blocked")
    
    # Test 3: Release and re-acquire
    lock1.release()
    assert lock2.acquire(non_blocking=True), "Failed to re-acquire after release"
    print("✓ Lock released and re-acquired")
    lock2.release()
    
    # Test 4: Context manager
    try:
        with check_lock(non_blocking=True):
            print("✓ Context manager acquired lock")
            
            # Try to acquire another lock - should raise
            try:
                with check_lock(non_blocking=True):
                    assert False, "Should have raised LockHeldError"
            except LockHeldError:
                print("✓ Context manager correctly raises LockHeldError")
    except Exception as e:
        print(f"✗ Context manager failed: {e}")
        return False
    
    # Clean up
    if lock_file.exists():
        lock_file.unlink()
    
    print("✓ All lock tests passed\n")
    return True


def test_imports():
    """Test that all modules import correctly"""
    print("Testing imports...")
    
    try:
        from app.main import main
        print("✓ app.main")
        
        from app.bot import TelegramBot
        print("✓ app.bot")
        
        from app.monitor import run_check, CheckResult, ProviderCheckResult
        print("✓ app.monitor")
        
        from app.locking import CheckLock, check_lock, LockHeldError
        print("✓ app.locking")
        
        from app.telegram import TelegramNotifier
        print("✓ app.telegram")
        
        from app.storage import VacancyStorage
        print("✓ app.storage")
        
        print("✓ All imports successful\n")
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_bot_format():
    """Test bot message formatting"""
    print("Testing bot message formatting...")
    
    try:
        from app.bot import TelegramBot
        from app.monitor import CheckResult, ProviderCheckResult
        
        bot = TelegramBot("test_token", "123456")
        
        # Test success case
        result = CheckResult(
            total_found=5,
            new_found=2,
            providers={
                'vk': ProviderCheckResult('vk', 3, 1, True),
                'yandex': ProviderCheckResult('yandex', 2, 1, True)
            },
            has_errors=False
        )
        
        message = bot.format_check_result(result)
        assert "✅ Проверка завершена" in message
        assert "VK: 3 вакансий" in message
        assert "🆕 Новых вакансий: 2" in message
        print("✓ Success message format correct")
        
        # Test error case
        result_error = CheckResult(
            total_found=2,
            new_found=0,
            providers={
                'vk': ProviderCheckResult('vk', 0, 0, False, "Error"),
                'yandex': ProviderCheckResult('yandex', 2, 0, True)
            },
            has_errors=True
        )
        
        message = bot.format_check_result(result_error)
        assert "⚠️" in message
        assert "ошибка" in message
        print("✓ Error message format correct")
        
        print("✓ All message format tests passed\n")
        return True
        
    except Exception as e:
        print(f"✗ Message format test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all smoke tests"""
    print("=" * 50)
    print("SMOKE TEST - /update functionality")
    print("=" * 50)
    print()
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("File Lock", test_lock()))
    results.append(("Bot Formatting", test_bot_format()))
    
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("✓ All smoke tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
