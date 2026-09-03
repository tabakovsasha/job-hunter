# Job Hunter - Vacancy Monitoring Service

Автоматический мониторинг новых вакансий с уведомлениями в Telegram.

## Поддерживаемые источники

- **VK Team** - https://team.vk.company/
- **Yandex Careers** - https://yandex.ru/jobs/

## Возможности

- ⏰ **Автоматическая проверка каждый час** через cron
- 📱 **Уведомления в Telegram** о новых вакансиях
- 🤖 **Управление через бота** - команды `/update`, `/list`, `/start`
- 💾 **Защита от дубликатов** - отслеживание известных вакансий
- 🛡️ **Первый запуск не спамит** - сохраняет вакансии без уведомлений
- 🔒 **Блокировка параллельных проверок** (file lock)
- 🔄 **Авторестарт** при сбоях (systemd)
- 👤 **Работает в личных сообщениях** - авторизация по вашему Chat ID


## Требования

- Python 3.11+
- Debian 13 (или любой Linux с systemd)
- Telegram Bot Token
- Доступ в интернет

## Установка

### 1. Подготовка проекта

```bash
cd /opt/job-hunter
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Настройка Telegram Bot

#### Создание бота

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Следуйте инструкциям и выберите имя для бота
4. Скопируйте токен бота (например: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### Получение Chat ID

Ваш личный Chat ID нужен для авторизации - только вы сможете управлять ботом.

Способ 1 (самый простой):
1. Найдите [@userinfobot](https://t.me/userinfobot) в Telegram
2. Отправьте ему любое сообщение
3. Скопируйте ваш **Id** (например: `484770368`)

Способ 2:
1. Найдите своего бота в Telegram и отправьте ему любое сообщение
2. Откройте в браузере:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
3. Найдите значение `"chat":{"id":123456789}` - это ваш Chat ID

### 3. Конфигурация

Создайте файл `.env`:

```bash
cp .env.example .env
nano .env
```

Заполните обязательные параметры:

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
SEARCH_QUERIES=presale
ENABLE_VK=true
ENABLE_YANDEX=true
```

### 4. Тестовый запуск

```bash
python -m app.main
```

При первом запуске сервис сохранит все найденные вакансии без отправки уведомлений.
При втором запуске будут отправлены уведомления только о новых вакансиях.

### 5. Установка systemd services

#### Автоматические проверки (каждый час)

```bash
sudo cp vacancy-watcher.service /etc/systemd/system/
sudo cp vacancy-watcher.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable vacancy-watcher.timer
sudo systemctl start vacancy-watcher.timer
```

#### Telegram bot (для команды /update)

```bash
sudo cp vacancy-watcher-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable vacancy-watcher-bot.service
sudo systemctl start vacancy-watcher-bot.service
```

### 6. Проверка работы

```bash
# Статус автоматических проверок
systemctl status vacancy-watcher.timer

# Статус Telegram бота
systemctl status vacancy-watcher-bot.service

# Когда следующий запуск
systemctl list-timers vacancy-watcher.timer

# Просмотр логов в реальном времени
journalctl -u vacancy-watcher.service -f
journalctl -u vacancy-watcher-bot.service -f

# Последние 50 строк логов
journalctl -u vacancy-watcher.service -n 50
journalctl -u vacancy-watcher-bot.service -n 50
```

## Telegram команды

Бот работает **только в личных сообщениях** с вами. Управляйте проверками прямо из Telegram:

### Доступные команды

**`/start`** - справка о боте и доступных командах

**`/update`** - немедленная проверка вакансий
- Проверяет все источники (VK, Yandex)
- Показывает **только новые** вакансии
- Отправляет итоговую статистику
- Защищён от параллельных запусков

**`/list`** - показать все вакансии из базы
- Показывает **все известные** вакансии
- Группирует по источникам
- Для каждой: название, компания, локация, ссылка

### Примеры использования

#### Проверка новых вакансий
1. Откройте чат с ботом `@tabakovsasha_bot`
2. Отправьте `/update`
3. Бот ответит "🔄 Проверяю вакансии…"
4. Получите уведомления о новых вакансиях (если есть)
5. Увидите итоговое сообщение

#### Просмотр всех вакансий
1. Отправьте `/list`
2. Получите список всех вакансий из базы
3. Вакансии сгруппированы по источникам

**Защита от одновременных проверок:**  
Если проверка уже выполняется, бот ответит:  
"⏳ Проверка уже выполняется. Попробуйте немного позже."


## Управление сервисом

```bash
# Запуск проверки вручную через CLI
sudo systemctl start vacancy-watcher.service

# Запуск проверки через Telegram
# Откройте чат с ботом и отправьте: /update

# Остановка автоматических проверок
sudo systemctl stop vacancy-watcher.timer

# Остановка Telegram бота
sudo systemctl stop vacancy-watcher-bot.service

# Отключение автозапуска
sudo systemctl disable vacancy-watcher.timer
sudo systemctl disable vacancy-watcher-bot.service

# Перезапуск бота (например, после изменения .env)
sudo systemctl restart vacancy-watcher-bot.service
```


## Структура проекта

```
job-hunter/
├── app/
│   ├── main.py              # CLI entry point
│   ├── bot.py               # Telegram bot (long polling)
│   ├── monitor.py           # Общая логика проверки
│   ├── locking.py           # File lock для защиты от race conditions
│   ├── models.py            # Модель Vacancy
│   ├── config.py            # Конфигурация
│   ├── storage.py           # Хранилище состояния
│   ├── telegram.py          # Telegram уведомления
│   └── providers/
│       ├── base.py          # Базовый интерфейс
│       ├── vk.py            # VK Team provider
│       └── yandex.py        # Yandex provider
├── data/
│   ├── state.json           # Состояние (автоматически)
│   └── check.lock           # Lock file (автоматически)
├── tests/
│   ├── test_bot.py          # Тесты бота и lock
│   ├── test_monitor.py      # Тесты логики мониторинга
│   ├── test_storage.py      # Тесты хранилища
│   ├── test_vk.py           # Тесты VK provider
│   └── test_yandex.py       # Тесты Yandex provider
├── .env                     # Конфигурация
├── requirements.txt
├── vacancy-watcher.service       # systemd service (CLI)
├── vacancy-watcher.timer         # systemd timer (hourly)
├── vacancy-watcher-bot.service   # systemd service (bot)
└── README.md
```


## Добавление нового источника

Создайте файл `app/providers/sber.py`:

```python
import logging
from app.models import Vacancy
from app.config import HTTP_TIMEOUT

logger = logging.getLogger(__name__)

class SberProvider:
    name = "sber"
    
    def get_vacancies(self, query: str) -> list[Vacancy]:
        logger.info(f"[SBER] Fetching vacancies for query: {query}")
        # ... ваш код парсинга ...
        return vacancies
```

Добавьте в `app/main.py` и `.env` - готово!

## Troubleshooting

### Уведомления не приходят

```bash
# Проверьте credentials
grep TELEGRAM .env

# Проверьте логи
journalctl -u vacancy-watcher.service | grep -i telegram
```

### Вакансии не находятся

```bash
# Запустите вручную
python -m app.main

# Проверьте доступность сайтов
curl -I https://team.vk.company/
```

## Лицензия

MIT

