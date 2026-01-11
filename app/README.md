# Web Scraper для Tilda CMS сайтов

Production-ready скрейпер для качественного извлечения контента из сайтов на Tilda CMS с очисткой технического мусора, поддержкой аккордеонов и сохранением структуры.

## Версии

**Две версии скрейпера:**

### v1: production_scraper.py
Базовая версия для обычных Tilda-сайтов без аккордеонов.
- Использован для: Navicons.com
- Результат: 38 страниц, ~100 строк на страницу

### v2: production_scraper_v2.py
Расширенная версия с поддержкой аккордеонов (скрытого контента).
- Использован для: Utrace.ru
- Результат: 22 страницы, ~200 строк на страницу
- **Рекомендуется для новых проектов**

## Возможности

### Общие (обе версии)
✅ **Поддержка Tilda CMS** - автоматическое определение и корректная работа с сайтами на Tilda
✅ **Очистка технического мусора** - удаление JSON данных форм, служебных тегов, навигации
✅ **Дедупликация контента** - автоматическое удаление повторяющегося текста
✅ **Структурированный markdown** - сохранение иерархии заголовков и форматирования
✅ **Интеграция со Scrape.do** - обход блокировок через прокси-сервис
✅ **Batch processing** - массовое сканирование с rate limiting

### Только v2
✅ **Извлечение аккордеонов** - автоматическое обнаружение и извлечение скрытого контента
✅ **Маркировка аккордеонов** - заголовки помечены символом ➕ в markdown
✅ **Защита Tilda-элементов** - не удаляются важные компоненты типа t585__header
✅ **Исправлен баг Tilda detection** - корректная работа с BeautifulSoup lambda

## Установка

### 1. Установите зависимости

```bash
# Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установите библиотеки
pip install requests beautifulsoup4
```

### 2. Настройте Scrape.do токен (опционально)

Если нужен обход блокировок через Scrape.do:

```bash
# Создайте файл с токеном
mkdir -p scrapedo-web-scraper/config
echo "ваш-токен-здесь" > scrapedo-web-scraper/config/token.txt

# Или используйте переменную окружения
export SCRAPEDO_TOKEN="ваш-токен"
```

## Использование

### v1: Базовый скрейпер (production_scraper.py)

**Одна страница:**
```bash
python3 production_scraper.py
```

**Массовое сканирование:**
```bash
python3 production_scraper.py all
```

Это:
1. Загрузит список страниц из `site_structure.json`
2. Скрейпит каждую страницу с задержкой 1.5 сек
3. Сохранит результаты в `scraped_content_v2/`
4. Создаст отчет `rescraping_summary.json`

### v2: Скрейпер с аккордеонами (production_scraper_v2.py)

**Одна страница:**
```bash
python3 production_scraper_v2.py
```
По умолчанию скрейпит тестовую страницу `https://utrace.ru/utrace-hub`.

**Массовое сканирование:**
```bash
python3 production_scraper_v2.py all
```

Это:
1. Загрузит список страниц из `utrace_structure.json` (или другого файла)
2. Скрейпит каждую страницу с задержкой 1.5 сек
3. **Извлечет контент из аккордеонов** (скрытые секции)
4. Сохранит результаты в `result/utrace/scraped_content/`
5. Создаст отчет `result/utrace/scraping_summary.json`

**Выбор версии:**
- Используйте **v2** для сайтов с аккордеонами (скрытый контент)
- Используйте **v1** только для простых сайтов без аккордеонов

### Использование как модуль

```python
from production_scraper import scrape_page_production

# Скрейпить одну страницу
markdown = scrape_page_production('https://example.com')

if markdown:
    with open('output.md', 'w', encoding='utf-8') as f:
        f.write(markdown)
```

## Структура выходных файлов

```
scraped_content_v2/
├── index.md              # Главная страница
├── about.md              # О компании
├── solutions/            # Решения
│   ├── product1.md
│   └── product2.md
└── news/                 # Новости
    └── article1.md
```

## Настройка фильтров

### Добавление технического мусора для фильтрации

В файле `production_scraper.py` найдите `TECH_NOISE_PATTERNS`:

```python
TECH_NOISE_PATTERNS = [
    r'nominify\s+(begin|end)',
    r'Content Oriented Web',
    r'\{"lid":.+"li_nm"',  # JSON данные форм
    # Добавьте свои паттерны здесь
    r'ваш-паттерн',
]
```

### Настройка Tilda классов

Если на сайте используются другие классы для контента:

```python
tilda_text_classes = [
    'tn-atom',           # Текстовые блоки
    't-descr',           # Описания
    't491__content',     # Контент блоков
    # Добавьте свои классы
    'custom-text-class',
]
```

## Особенности работы с аккордеонами (v2)

### Что такое аккордеоны?

Аккордеоны - это скрытые секции контента, которые раскрываются по клику на заголовок или кнопку +.

На Tilda аккордеоны используются для:
- FAQ секций
- Детальных описаний продуктов
- Технических характеристик
- Дополнительной информации

### Как v2 извлекает аккордеоны

**1. Обнаружение:**
```python
accordions = soup.find_all(attrs={'data-accordion': True})
# Tilda использует: <div class="t585__accordion" data-accordion="true">
```

**2. Извлечение заголовка:**
```python
title_elem = acc.find(class_=lambda x: x and 'title' in str(x).lower())
# Находит элемент с 'title' в названии класса
```

**3. Извлечение содержимого:**
```python
content_elem = acc.find(class_=lambda x: x and ('content' in str(x).lower()
                                                 or 'text' in str(x).lower()
                                                 or 'descr' in str(x).lower()))
# Находит скрытый контент
```

### Формат в markdown

Аккордеоны помечаются символом ➕:

```markdown
### ➕ Управление мастер-данными

Utrace Hub позволяет создавать, хранить и обновлять мастер-данные...

### ➕ Интеграция с внешними системами

Utrace Hub допускает интеграцию с внешними системами...
```

Символ ➕ указывает, что это был скрытый контент (аккордеон).

### Важно!

Аккордеоны извлекаются **ПЕРВЫМИ**, до обычного контента, чтобы сохранить правильный порядок информации на странице.

## Особенности работы с Tilda CMS

### Автоматическое определение (v2 - исправлено!)

⚠️ **v1 содержит критический баг** в определении Tilda-сайтов!

**v2 (правильно):**
```python
is_tilda = soup.find('div', class_=lambda x: x and ('t396' in x or any('tn-' in cls for cls in x)))
```

**v1 (неправильно - не работает):**
```python
is_tilda = soup.find('div', class_=lambda x: x and ('tn-' in ' '.join(x)))
```

### Извлечение контента

Для Tilda используется `body` целиком, так как контент распределен по секциям:

```python
if is_tilda:
    main_content = soup.body or soup
```

### Специальные классы

Tilda использует специфические классы для текста:
- `tn-atom` - текстовые блоки
- `t-descr` - описания
- `t491__content` - контент блоков
- `t-card__descr` - описания карточек

## Troubleshooting

### Проблема: Пустой или короткий контент

**Причина:** Неправильное определение main_content контейнера

**Решение:** Проверьте, что сайт определяется как Tilda:
```python
# Добавьте отладку
print(f"Is Tilda: {is_tilda}")
print(f"Main content tag: {main_content.name if hasattr(main_content, 'name') else 'N/A'}")
```

### Проблема: Много технического мусора

**Причина:** Нужны дополнительные фильтры

**Решение:** Добавьте паттерны в `TECH_NOISE_PATTERNS` или проверьте классы элементов:
```bash
# Найдите мусор в выходном файле
grep -n "нежелательный-текст" output.md

# Определите паттерн и добавьте в фильтры
```

### Проблема: Ошибка "No such file or directory"

**Причина:** Попытка сохранить в несуществующую подпапку

**Решение:** Создавайте подпапки автоматически:
```python
filepath.parent.mkdir(parents=True, exist_ok=True)
```

### Проблема: Блокировка при скрейпинге

**Причина:** Сайт блокирует прямые запросы

**Решение:**
1. Используйте Scrape.do токен
2. Увеличьте задержку между запросами:
```python
time.sleep(2.5)  # Вместо 1.5
```

### Проблема: Аккордеоны не извлекаются (v1)

**Причина:** v1 не поддерживает аккордеоны

**Решение:** Используйте v2 скрейпер:
```bash
python3 production_scraper_v2.py
```

### Проблема: Аккордеоны не находятся (v2)

**Причина:** Аккордеоны были удалены при очистке

**Решение (уже исправлено в v2):** Не удаляйте элементы с `t\d+__` в начале класса:
```python
for element in soup.find_all(class_=re.compile(r'header|footer|menu|nav', re.I)):
    classes = element.get('class', [])
    # Пропустить Tilda-элементы
    if not any(re.match(r'^t\d+__', cls) for cls in classes):
        element.decompose()
```

### Проблема: Tilda detection не работает (v1)

**Причина:** Критический баг в lambda функции

**Симптомы:**
- `is_tilda = None` хотя сайт на Tilda
- Контент извлекается из неправильного контейнера
- Пустой результат

**Решение:** Используйте v2 с исправленной lambda:
```python
# v2 (исправлено):
is_tilda = soup.find('div', class_=lambda x: x and ('t396' in x or any('tn-' in cls for cls in x)))

# v1 (баг):
is_tilda = soup.find('div', class_=lambda x: x and ('tn-' in ' '.join(x)))  # НЕ РАБОТАЕТ!
```

**Почему v1 не работает:**
BeautifulSoup передает список классов напрямую в lambda, а не строку. Проверка `'tn-' in ' '.join(x)` ищет 'tn-' в строке "t396 t396__artboard", где этого подстроки нет.

### Критические различия версий

| Проблема | v1 | v2 |
|----------|----|----|
| Tilda detection | ❌ Не работает | ✅ Исправлено |
| Аккордеоны | ❌ Не поддерживается | ✅ Поддерживается |
| Защита t\d+__ элементов | ❌ Отсутствует | ✅ Реализована |
| Качество контента | ~100 строк/страница | ~200 строк/страница |

**Рекомендация:** Используйте v2 для всех новых проектов.

## API Reference

### `scrape_page_production(url: str) -> str`

Скрейпит одну страницу и возвращает markdown.

**Параметры:**
- `url` - URL страницы для скрейпинга

**Возвращает:**
- `str` - Markdown контент или `None` при ошибке

### `rescrape_all_pages()`

Массовое сканирование всех страниц из `site_structure.json`.

Требует:
- `site_structure.json` - файл со списком URL
- `scraped_content_v2/` - выходная директория

Создает:
- Markdown файлы для каждой страницы
- `rescraping_summary.json` - отчет о сканировании

## Примеры

### Скрейпинг с кастомной обработкой

```python
from production_scraper import extract_structured_content
import sys
sys.path.insert(0, 'scrapedo-web-scraper/scripts')
from scrape import fetch_via_scrapedo

# Получить HTML
result = fetch_via_scrapedo('https://example.com')

if result['success']:
    # Извлечь структурированный контент
    content = extract_structured_content(result['html'], 'https://example.com')

    # Обработать контент
    for item in content['content']:
        if item['type'] == 'heading':
            print(f"{'#' * item['level']} {item['text']}")
        elif item['type'] == 'paragraph':
            print(item['text'])
```

### Создание кастомного фильтра

```python
def custom_filter(text):
    """Кастомный фильтр для вашего сайта"""
    # Удалить рекламу
    if 'реклама' in text.lower():
        return True

    # Удалить короткие фрагменты
    if len(text) < 20:
        return True

    return False

# Используйте в скрейпере
if not custom_filter(text):
    content_structure.append({'type': 'paragraph', 'text': text})
```

## Лицензия

MIT

## Поддержка

При возникновении проблем:
1. Проверьте логи в консоли
2. Изучите раздел Troubleshooting
3. Добавьте отладочные print() в код
4. Проверьте HTML структуру сайта через DevTools
