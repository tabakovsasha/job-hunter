# Исправление проблемы с Yandex парсером

## Проблема

При выполнении `/update` бот сообщал:
- **VK: 1 вакансия** ✅
- **YANDEX: 0 вакансий** ❌

Но при `/list` показывал:
- **YANDEX: 1 вакансия** ✅ (она есть в базе!)

## Причина

Yandex изменил формат URL вакансий. Раньше были разные форматы, теперь используется:
```
/jobs/vacancies/arhitektortehnicheskiy-preseyl-v-yandex-cloud-security-43663
```

Парсер извлекал **полный slug** как ID:
- Находил: `arhitektortehnicheskiy-preseyl-v-yandex-cloud-security-43663`
- В базе хранится: `43663`
- Результат: система считала их **разными** вакансиями

## Решение

Изменён алгоритм извлечения ID в `/opt/job-hunter/app/providers/yandex.py` (строки 56-71):

**Было:**
```python
match = re.search(r'/jobs/vacancies/[^/]+-(\\d+)', href)
if not match:
    # много вложенных if-else
    # использовал полный slug как ID
```

**Стало:**
```python
# Сначала ищем числовой ID в конце URL
match = re.search(r'-(\\d+)$', href.rstrip('/'))
if match:
    vac_id = match.group(1)  # Берём только цифры: 43663
else:
    # fallback варианты
```

## Результат

✅ Парсер теперь правильно извлекает ID: `43663`  
✅ Ключ совпадает с базой: `yandex:43663`  
✅ Вакансия корректно определяется как известная

## Тестирование

```bash
cd /opt/job-hunter && source venv/bin/activate
python3 << 'EOF'
from app.providers.yandex import YandexProvider
provider = YandexProvider()
vacancies = provider.get_vacancies('presale')
print(f"Found: {len(vacancies)} vacancies")
for v in vacancies:
    print(f"  ID: {v.external_id}")
EOF
```

Вывод:
```
Found: 1 vacancies
  ID: 43663
```

## Действия

1. ✅ Исправлен парсер Yandex
2. ✅ Протестирован вручную
3. ✅ Бот перезапущен
4. ⏳ Требуется тест через `/update` в Telegram

---
**Дата исправления:** 2026-09-04 00:16  
**Файл:** `/opt/job-hunter/app/providers/yandex.py`  
**Строки:** 56-71
