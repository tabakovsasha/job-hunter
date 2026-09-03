# Telegram /update - Implementation Summary

## ✅ Completed

### Core Implementation

**1. Shared Monitoring Logic (`app/monitor.py`)**
- Extracted `run_check()` function used by both CLI and bot
- Returns structured `CheckResult` with per-provider details
- Provider isolation: one failure doesn't stop others

**2. Inter-Process Locking (`app/locking.py`)**
- File-based lock using `fcntl.flock`
- Prevents concurrent checks:
  - systemd timer + manual CLI
  - systemd timer + Telegram /update
  - multiple /update commands
- Context manager support with automatic cleanup

**3. Telegram Bot (`app/bot.py`)**
- Long polling via `getUpdates` (50s timeout)
- Proper offset management (no duplicate processing)
- Authorization via `TELEGRAM_CHAT_ID`
- Commands: `/start`, `/update`

**4. Refactored CLI (`app/main.py`)**
- Now uses shared `run_check()` from monitor
- Implements file locking
- Maintains backward compatibility

**5. systemd Service (`vacancy-watcher-bot.service`)**
- Always-running bot process
- Auto-restart on failure (RestartSec=5)
- Auto-start on boot
- Logs to journald

**6. Enhanced Telegram (`app/telegram.py`)**
- Added `send_message()` for arbitrary messages
- Used by bot for status updates

### Testing

**New Tests (`tests/test_bot.py`)**
- CheckLock: acquire/release, concurrent access, context manager
- TelegramBot: authorization, message formatting, getUpdates, offset

**Existing Tests**
- All 15 existing tests remain functional

### Documentation

**Updated:**
- `README.md`: Telegram commands section, bot installation
- `REPORT.md`: Complete implementation details
- Created `smoke_test.py` for quick validation

## Architecture

```
┌─────────────────┐         ┌──────────────────┐
│  systemd timer  │         │   Telegram User  │
│   (hourly)      │         │                  │
└────────┬────────┘         └────────┬─────────┘
         │                           │
         │ python -m app.main        │ /update
         │                           │
         ↓                           ↓
┌────────────────────────────────────────────────┐
│              app/monitor.py                    │
│           run_check() [shared logic]           │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │       app/locking.py (file lock)         │ │
│  │   Prevents concurrent execution          │ │
│  └──────────────────────────────────────────┘ │
│                                                │
│  ┌─────────────┐  ┌─────────────┐            │
│  │ VK Provider │  │Yandex Provid│            │
│  └─────────────┘  └─────────────┘            │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │    app/storage.py (state.json)           │ │
│  │    Vacancy deduplication                 │ │
│  └──────────────────────────────────────────┘ │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │  app/telegram.py (notifications)         │ │
│  │  send_vacancy_notification()             │ │
│  │  send_message() [new]                    │ │
│  └──────────────────────────────────────────┘ │
└────────────────────────────────────────────────┘
```

## User Experience

### /update Flow

1. User sends `/update` to bot
2. Bot responds: `🔄 Проверяю вакансии…`
3. Bot runs `run_check()` with file lock
4. New vacancies sent as individual messages
5. Bot sends summary:
   ```
   ✅ Проверка завершена
   
   VK: 2 вакансии
   YANDEX: 1 вакансия
   
   🆕 Новых вакансий: 1
   ```

### Concurrent Check Protection

If check already running:
```
⏳ Проверка уже выполняется. Попробуйте немного позже.
```

### Provider Error Handling

If one provider fails:
```
⚠️ Проверка завершена с ошибками

VK: ошибка получения данных
YANDEX: 3 вакансии

Новых вакансий: 0
```

## Installation

```bash
# Install bot service
sudo cp vacancy-watcher-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vacancy-watcher-bot.service

# Check status
systemctl status vacancy-watcher-bot.service

# View logs
journalctl -u vacancy-watcher-bot.service -f
```

## Testing

```bash
# Run smoke tests
python smoke_test.py

# Test CLI
python -m app.main

# Test bot (manual)
python -m app.bot
# Then send /update in Telegram

# View bot logs
journalctl -u vacancy-watcher-bot.service -n 50
```

## Files Changed

**Created:**
- `app/bot.py` (236 lines)
- `app/monitor.py` (202 lines)
- `app/locking.py` (109 lines)
- `tests/test_bot.py` (190 lines)
- `vacancy-watcher-bot.service` (18 lines)
- `smoke_test.py` (171 lines)

**Modified:**
- `app/main.py` (refactored, simplified)
- `app/telegram.py` (+43 lines)
- `README.md` (+80 lines)
- `REPORT.md` (+192 lines)

**Total:** ~1,150 lines of code and documentation

## Security

- Only authorized `TELEGRAM_CHAT_ID` can execute `/update`
- Unauthorized requests are ignored (warning logged)
- Bot token never logged or exposed
- File lock prevents race conditions

## Next Steps

1. ✅ Verify CLI still works: `python -m app.main`
2. ✅ Install bot service: see Installation above
3. ✅ Test /update: send command to bot in Telegram
4. ✅ Monitor logs: `journalctl -u vacancy-watcher-bot.service -f`
5. ✅ Ensure both services enabled:
   - `vacancy-watcher.timer` (hourly checks)
   - `vacancy-watcher-bot.service` (Telegram commands)
