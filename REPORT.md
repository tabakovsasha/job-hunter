# Отчёт о реализации сервиса мониторинга вакансий

## Обновление: Telegram /update команда (2026-09-03)

### Новая функциональность

Добавлена возможность ручного запуска проверки вакансий через Telegram-команду `/update`.

### Реализованные компоненты

**1. Общая логика мониторинга (app/monitor.py)**
- Вынесена переиспользуемая функция `run_check()`
- Используется как CLI (`app.main`), так и Telegram ботом (`app.bot`)
- Возвращает структурированный результат `CheckResult` с детальной информацией по каждому провайдеру
- Изолирует ошибки провайдеров - падение одного не останавливает проверку других

**2. Межпроцессная блокировка (app/locking.py)**
- File lock через `fcntl.flock` (POSIX)
- Предотвращает одновременное выполнение:
  - systemd timer + manual CLI
  - systemd timer + Telegram /update
  - multiple Telegram /update команд
- При попытке запуска второй проверки:
  - CLI: завершается с ошибкой
  - Bot: отвечает "⏳ Проверка уже выполняется"
- Lock автоматически освобождается даже при exception

**3. Telegram Bot (app/bot.py)**
- Long polling через Telegram Bot API `getUpdates`
- Timeout 50 секунд для эффективного polling
- Корректное управление `offset` для предотвращения дублей
- Авторизация: проверка `TELEGRAM_CHAT_ID` из .env
- Неавторизованные запросы игнорируются (только warning в лог)

**Команды:**
- `/start` - информация о боте
- `/update` - запуск проверки вакансий

**4. Рефакторинг app/main.py**
- Теперь использует общую функцию `run_check()` из `app/monitor`
- Использует file lock для предотвращения одновременных запусков
- Сохранена полная совместимость с существующим поведением

**5. systemd service для бота (vacancy-watcher-bot.service)**
- Постоянно работающий процесс
- `Restart=always` с `RestartSec=5`
- Автозапуск после reboot
- Логи через journald

**6. Обновления telegram.py**
- Добавлен метод `send_message()` для отправки произвольных сообщений
- Используется ботом для отправки служебных сообщений

### Архитектура

```
vacancy-watcher/
├── app/
│   ├── main.py                   # CLI entry point (использует run_check)
│   ├── bot.py                    # Telegram bot (long polling, /update)
│   ├── monitor.py                # ⭐ Общая логика проверки
│   ├── locking.py                # ⭐ File lock (межпроцессный)
│   ├── models.py
│   ├── config.py
│   ├── storage.py
│   ├── telegram.py               # ⭐ Обновлён: send_message()
│   └── providers/
│       ├── base.py
│       ├── vk.py
│       └── yandex.py
├── data/
│   ├── state.json
│   └── check.lock                # ⭐ Lock file (автоматически)
├── tests/
│   ├── test_bot.py               # ⭐ Новые тесты
│   ├── test_monitor.py
│   ├── test_storage.py
│   ├── test_vk.py
│   └── test_yandex.py
├── vacancy-watcher.service
├── vacancy-watcher.timer
├── vacancy-watcher-bot.service   # ⭐ Новый systemd service
└── README.md                     # ⭐ Обновлён

⭐ = новое/изменённое
```

### UX Telegram /update

**Пользователь отправляет:** `/update`

**Бот отвечает:**
1. `🔄 Проверяю вакансии…`
2. (Если найдены новые) Стандартные уведомления о вакансиях
3. Итоговое сообщение:

```
✅ Проверка завершена

VK: 2 вакансии
YANDEX: 1 вакансия

🆕 Новых вакансий: 1
```

**Если ошибка провайдера:**
```
⚠️ Проверка завершена с ошибками

VK: ошибка получения данных
YANDEX: 3 вакансии

Новых вакансий: 0
```

**Если проверка уже идёт:**
```
⏳ Проверка уже выполняется. Попробуйте немного позже.
```

### Безопасность

- Команда `/update` выполняется ТОЛЬКО для `TELEGRAM_CHAT_ID` из .env
- Неавторизованные chat_id игнорируются (warning в лог, без ответа)
- Bot token никогда не выводится в лог или ответы
- File lock предотвращает race conditions между процессами

### Установка

```bash
# 1. Установить Telegram bot service
sudo cp vacancy-watcher-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vacancy-watcher-bot.service

# 2. Проверить статус
systemctl status vacancy-watcher-bot.service

# 3. Просмотр логов
journalctl -u vacancy-watcher-bot.service -f
```

### Smoke Test

```bash
# 1. Проверить, что CLI работает
python -m app.main

# 2. Проверить, что бот запускается
python -m app.bot
# (Ctrl+C для остановки)

# 3. Отправить боту в Telegram:
/update

# 4. Проверить логи
journalctl -u vacancy-watcher-bot.service -n 50
```

### Тесты

**Новые тесты (tests/test_bot.py):**
- `TestCheckLock` - тестирование file lock
  - Basic acquire/release
  - Concurrent access blocking
  - Context manager
- `TestTelegramBot` - тестирование бота
  - Authorization check
  - Message formatting (success/errors/no new)
  - send_message success/failure
  - getUpdates
  - update_id offset management

**Все существующие тесты (15) продолжают работать.**

### Изменённые файлы

**Созданы:**
- `/opt/job-hunter/app/bot.py` (236 строк)
- `/opt/job-hunter/app/monitor.py` (202 строки)
- `/opt/job-hunter/app/locking.py` (109 строк)
- `/opt/job-hunter/tests/test_bot.py` (190 строк)
- `/opt/job-hunter/vacancy-watcher-bot.service` (18 строк)
- `/opt/job-hunter/smoke_test.py` (171 строка)

**Изменены:**
- `/opt/job-hunter/app/main.py` (полностью рефакторен, -93 строки)
- `/opt/job-hunter/app/telegram.py` (+43 строки: send_message метод)
- `/opt/job-hunter/README.md` (+80 строк: Telegram commands, bot service)

**Итого добавлено:** ~970 строк кода и документации

---

## Архитектура (исходная)


Создана минимальная, но расширяемая архитектура:

```
vacancy-watcher/
├── app/                          # Основное приложение
│   ├── config.py                 # Конфигурация из .env
│   ├── models.py                 # Модель Vacancy (dataclass)
│   ├── storage.py                # JSON-хранилище состояния
│   ├── telegram.py               # Отправка уведомлений
│   ├── main.py                   # Главная логика мониторинга
│   └── providers/                # Провайдеры источников вакансий
│       ├── base.py               # Базовый Protocol для провайдеров
│       ├── vk.py                 # VK Team провайдер
│       └── yandex.py             # Yandex Careers провайдер
├── data/                         # Состояние (state.json)
├── tests/                        # Unit и integration тесты
├── requirements.txt              # Зависимости
├── .env.example                  # Шаблон конфигурации
├── .gitignore                    # Исключения для git
├── vacancy-watcher.service       # systemd service
├── vacancy-watcher.timer         # systemd timer (каждый час)
└── README.md                     # Полная документация
```

**Общий объём кода:** ~691 строк Python

**Ключевые принципы:**
- Каждый провайдер независим и возвращает единую модель `Vacancy`
- Ошибка одного провайдера не останавливает другие
- Первый запуск каждого источника не отправляет уведомления
- Вакансии хранятся с составным ключом `source:external_id`
- Атомарное сохранение состояния через временный файл

---

## VK Team

**URL:** https://team.vk.company/vacancy/?search=presale

### Способ получения данных
**HTML-парсинг с использованием BeautifulSoup**

VK Team не предоставляет публичного JSON API для поиска вакансий. Страница использует server-side rendering, и вакансии присутствуют непосредственно в HTML.

### Технические детали

**Структура HTML:**
```html
<a class="scroll-link" href="/vacancy/{id}/">
    <div class="card-title-block">
        <h3 class="card-title">{title}</h3>
    </div>
</a>
```

**Извлекаемые поля:**
- **ID**: извлекается из URL `/vacancy/{id}/`
- **Title**: текст из `<h3 class="card-title">`
- **URL**: `https://team.vk.company/vacancy/{id}/`
- **Location**: извлекается из `<div class="vacancy-card-location">`
- **Company**: извлекается из `<div class="vacancy-card-company">`

### Pagination
VK использует параметр `offset`:
- `?search=presale&offset=0` — первая страница
- `?search=presale&offset=20` — вторая страница (20 вакансий на страницу)

Провайдер автоматически получает все страницы до тех пор, пока не встретит пустой результат или не достигнет максимума в 500 вакансий (защита от зацикливания).

### Результаты smoke-тестов

**Запрос "presale":**
- ✅ Найдено: **1 вакансия**
- Пример: "Ведущий Presale-архитектор" (VK Tech, Москва)
- ID: 52669

**Запрос "python":**
- ✅ Найдено: **5 вакансий**

**Стабильность:**
- HTTP запросы успешны
- HTML-структура стабильна
- User-Agent: `VacancyWatcher/1.0`
- Timeout: 30 секунд
- Retry: до 3 попыток при временных ошибках

---

## Yandex Careers

**URL:** https://yandex.ru/jobs/vacancies?from=cp_fastfilters&text=presale

### Способ получения данных
**HTML-парсинг с использованием BeautifulSoup**

Yandex Careers также не предоставляет публичного API. Вакансии отображаются через server-side rendering.

### Технические детали

**Структура HTML:**
```html
<a class="VacancySnippet_titleLink__..." href="/jobs/vacancies/{id}/">
    {title}
</a>
```

**Извлекаемые поля:**
- **ID**: извлекается из атрибута `href` ссылки
- **Title**: текст внутри ссылки с классом `VacancySnippet_titleLink`
- **URL**: `https://yandex.ru{href}`
- **Location**: пока не извлекается (структура требует дополнительного изучения)
- **Company**: всегда "Яндекс"

### Pagination
Yandex использует параметр `page`:
- `?text=presale&page=0` — первая страница
- `?text=presale&page=1` — вторая страница

Провайдер автоматически получает все страницы, пока находит новые вакансии (максимум 500 вакансий как защита).

### Результаты smoke-тестов

**Запрос "presale":**
- ✅ Найдено: **0 вакансий**
- (На момент тестирования Yandex не имеет открытых presale-вакансий)

**Запрос "python":**
- ✅ Найдено: **20 вакансий**
- Примеры:
  - "MultiTrack — новый формат найма для опытных бэкендеров"
  - "Python-разработчик в Yandex DataLens"
  - "Разработчик на C++ и Python в платформу онлайн-экспериментов"

**Стабильность:**
- HTTP запросы успешны
- HTML-парсинг работает корректно
- Нет CAPTCHA или anti-bot защиты при разумной нагрузке
- User-Agent: `VacancyWatcher/1.0`
- Timeout: 30 секунд

---

## Telegram

### Реализация
Используется прямое обращение к Telegram Bot API через HTTP:
```
POST https://api.telegram.org/bot{token}/sendMessage
```

### Формат уведомлений
```
🔥 Новая вакансия VK

Ведущий Presale-архитектор

📍 Москва
🏢 VK Tech

https://team.vk.company/vacancy/52669/
```

Поля, которых нет (например, `location` или `company`), не выводятся.

### Обработка ошибок
- При ошибке отправки вакансия **не помечается** как обработанная
- При следующем запуске попытка отправки будет повторена
- Проверяется HTTP status и JSON response (`ok == true`)
- `TELEGRAM_BOT_TOKEN` никогда не логируется

### Статус тестирования
⚠️ **Требуются реальные credentials для полного тестирования**

Для тестирования уведомлений необходимо:
1. Создать бота через @BotFather
2. Получить `TELEGRAM_BOT_TOKEN`
3. Узнать свой `TELEGRAM_CHAT_ID` через @userinfobot
4. Добавить эти значения в `.env`

При отсутствии credentials приложение работает в режиме "dry run" и логирует предупреждение.

---

## Тесты

### Структура тестов
```
tests/
├── test_storage.py      # Тесты хранилища (6 тестов)
├── test_vk.py          # VK провайдер (2 теста, включая live)
├── test_yandex.py      # Yandex провайдер (2 теста, включая live)
└── test_monitor.py     # Интеграционные тесты (5 тестов)
```

### Покрытые сценарии

**Storage:**
✅ Инициализация пустого состояния  
✅ Отслеживание инициализации источников  
✅ Добавление и проверка вакансий  
✅ Фильтрация новых вакансий  
✅ Уникальные ключи для разных источников  
✅ Персистентность данных  

**Провайдеры:**
✅ VK: базовая инициализация  
✅ VK: реальный HTTP запрос (live smoke-test)  
✅ Yandex: базовая инициализация  
✅ Yandex: реальный HTTP запрос (live smoke-test)  

**Интеграция:**
✅ Первый запуск не отправляет уведомления  
✅ Второй запуск обнаруживает новые вакансии  
✅ Повторное появление вакансии не вызывает дубликат уведомления  
✅ Независимость источников (VK и Yandex)  
✅ Изоляция ошибок провайдеров  

### Запуск тестов
```bash
cd /opt/job-hunter
PYTHONPATH=/opt/job-hunter ./venv/bin/python tests/test_storage.py
PYTHONPATH=/opt/job-hunter ./venv/bin/python tests/test_monitor.py
PYTHONPATH=/opt/job-hunter ./venv/bin/python tests/test_vk.py
PYTHONPATH=/opt/job-hunter ./venv/bin/python tests/test_yandex.py
```

**Результат:** ✅ Все тесты пройдены успешно

---

## Запуск

### Ручной запуск
```bash
cd /opt/job-hunter
./venv/bin/python -m app.main
```

### Вывод первого запуска (пример)
```
2026-09-03 17:06:19 INFO Starting vacancy check
2026-09-03 17:06:19 INFO Enabled providers: ['vk', 'yandex']
2026-09-03 17:06:19 INFO [VK] Fetching vacancies for query: presale
2026-09-03 17:06:19 INFO [VK] Found 1 vacancies
2026-09-03 17:06:19 INFO [VK] Initial scan, saving 1 vacancies without notifications
2026-09-03 17:06:19 INFO [YANDEX] Fetching vacancies for query: presale
2026-09-03 17:06:20 INFO [YANDEX] Found 0 vacancies
2026-09-03 17:06:20 INFO [YANDEX] Initial scan, saving 0 vacancies without notifications
2026-09-03 17:06:20 INFO Vacancy check completed
2026-09-03 17:06:20 INFO Total vacancies in database: 1
```

### Вывод второго запуска (пример)
```
2026-09-03 17:06:31 INFO Starting vacancy check
2026-09-03 17:06:31 INFO Loaded state with 1 vacancies
2026-09-03 17:06:31 INFO [VK] Found 1 vacancies
2026-09-03 17:06:31 INFO [VK] New vacancies: 0
2026-09-03 17:06:32 INFO [YANDEX] Found 0 vacancies
2026-09-03 17:06:32 INFO [YANDEX] New vacancies: 0
2026-09-03 17:06:32 INFO Vacancy check completed
```

---

## Автозапуск через systemd

### Установка

**1. Скопировать unit-файлы:**
```bash
sudo cp /opt/job-hunter/vacancy-watcher.service /etc/systemd/system/
sudo cp /opt/job-hunter/vacancy-watcher.timer /etc/systemd/system/
```

**2. Перезагрузить systemd и запустить timer:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable vacancy-watcher.timer
sudo systemctl start vacancy-watcher.timer
```

### Проверка

**Статус timer:**
```bash
systemctl status vacancy-watcher.timer
```

**Список активных таймеров:**
```bash
systemctl list-timers --all | grep vacancy
```

**Логи последнего запуска:**
```bash
journalctl -u vacancy-watcher.service -n 50
```

**Логи в реальном времени:**
```bash
journalctl -u vacancy-watcher.service -f
```

### Расписание
- **Частота:** каждый час (OnCalendar=hourly)
- **Persistent:** да (запустится сразу после перезагрузки, если был пропущен)
- **RandomizedDelay:** до 5 минут (снижает нагрузку при множественных сервисах)

---

## Конфигурация

### Создание .env файла
```bash
cp .env.example .env
nano .env
```

### Основные параметры

**Telegram (обязательно для уведомлений):**
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321
```

**Поисковые запросы:**
```env
SEARCH_QUERIES=presale
# или несколько:
# SEARCH_QUERIES=presale,pre-sale,solution architect
```

**Включение/отключение источников:**
```env
ENABLE_VK=true
ENABLE_YANDEX=true
```

---

## Расширяемость

Для добавления нового источника (например, SberTech) необходимо:

**1. Создать провайдер:**
```python
# app/providers/sber.py
from typing import Protocol
from app.models import Vacancy

class SberProvider:
    name = "sber"
    
    def get_vacancies(self, query: str) -> list[Vacancy]:
        # Реализация получения вакансий с SberTech
        pass
```

**2. Добавить в конфигурацию:**
```env
ENABLE_SBER=true
```

**3. Зарегистрировать в main.py:**
```python
from app.providers.sber import SberProvider

if config.ENABLE_SBER:
    providers.append(SberProvider())
```

Общая логика (storage, Telegram, сравнение, логирование) работает без изменений.

---

## Ограничения и особенности

### 1. HTML-парсинг
Оба источника используют парсинг HTML, а не стабильные API. Это означает:
- ✅ Работает на текущий момент
- ⚠️ Может сломаться при редизайне сайтов
- ✅ Легко чинится обновлением селекторов

### 2. Anti-bot защита
На текущий момент:
- ✅ VK: CAPTCHA не обнаружена
- ✅ Yandex: CAPTCHA не обнаружена
- ✅ Частота запросов (раз в час) безопасна

Если в будущем появится защита:
- Можно добавить дополнительные заголовки
- Можно увеличить randomized delay в systemd timer
- В крайнем случае — использовать Selenium/Playwright (не рекомендуется)

### 3. Yandex: отсутствие поля location
Yandex Careers показывает город в карточке вакансии, но извлечение требует дополнительного селектора. Можно доработать позже при необходимости.

### 4. Зависимости
Минимальные зависимости:
- `requests` — HTTP клиент
- `beautifulsoup4` — HTML парсинг
- `python-dotenv` — конфигурация

Без тяжеловесных фреймворков (FastAPI, Django, Celery, etc.)

### 5. Хранилище
JSON файл `data/state.json` подходит для:
- ✅ Сотни вакансий
- ✅ Несколько источников
- ✅ Одиночный процесс

Для масштабирования до тысяч вакансий рекомендуется мигрировать на SQLite или PostgreSQL.

---

## Итоговая статистика

| Компонент | Статус |
|-----------|--------|
| **VK Team провайдер** | ✅ Работает (1 presale вакансия найдена) |
| **Yandex Careers провайдер** | ✅ Работает (20 python вакансий найдено) |
| **HTML парсинг** | ✅ Стабилен |
| **Pagination** | ✅ Реализована для обоих источников |
| **Storage** | ✅ JSON с атомарной записью |
| **Telegram** | ⚠️ Требует credentials для live-теста |
| **Тесты** | ✅ 15 тестов, все пройдены |
| **systemd integration** | ✅ Service + Timer готовы |
| **Документация** | ✅ README.md с полными инструкциями |
| **Расширяемость** | ✅ Provider architecture |

---

## Следующие шаги

1. **Добавить Telegram credentials в .env**
2. **Запустить ручной тест:** `python -m app.main`
3. **Проверить уведомление в Telegram**
4. **Установить systemd timer:** `sudo systemctl enable --now vacancy-watcher.timer`
5. **Проверить через час:** `journalctl -u vacancy-watcher.service`

---

Сервис готов к production использованию на Debian 13.

