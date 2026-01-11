#!/usr/bin/env python3
"""
Production-ready скрейпер для всех страниц navicons.com
"""

import sys
import json
import time
from pathlib import Path
sys.path.insert(0, '.claude/commands/scrapedo-web-scraper/scripts')
from scrape import fetch_via_scrapedo
from bs4 import BeautifulSoup
import re
from collections import OrderedDict

# Расширенный список технического мусора
TECH_NOISE_PATTERNS = [
    r'nominify\s+(begin|end)',
    r'Content Oriented Web',
    r'Make great presentations',
    r'longreads.+landing pages',
    r'photo stories.+blogs',
    r'forms\.js',
    r'popup\.js',
    r'https?://postnikovmd\.com',
    r'header\s*/header\s*footer\s*/footer',
    r'googleoff:.+googleon:',
    r'/noindex\s+noindex/',
    r'<!--.+-->',
    r'\{"lid":.+"li_nm"',  # JSON данные форм Tilda
    r'\[{.+li_type.+}\]',  # Массивы JSON данных форм
]

def is_tech_noise(text):
    """Проверка на технический мусор"""
    if not text:
        return True

    text_clean = text.strip()

    # Очень короткие строки
    if len(text_clean) < 3:
        return True

    # Проверка паттернов
    for pattern in TECH_NOISE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True

    # Только цифры/символы
    if re.match(r'^[\d\s\.,;:!?\-—]+$', text_clean):
        return True

    # Строки вроде "div class container"
    if re.match(r'^[a-z]+\s+[a-z/]+\s*$', text_clean, re.IGNORECASE):
        return True

    return False

def clean_text(text):
    """Очистка текста"""
    if not text:
        return ""

    # Убираем множественные пробелы
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    # Убираем HTML entities
    text = re.sub(r'&\w+;', '', text)

    # Убираем технические маркеры
    text = re.sub(r'\s*=3D\s*', '', text)

    return text

def calculate_text_similarity(text1, text2):
    """Простая проверка похожести текстов"""
    # Нормализуем тексты
    norm1 = re.sub(r'\W+', '', text1.lower())
    norm2 = re.sub(r'\W+', '', text2.lower())

    if not norm1 or not norm2:
        return 0

    # Если один текст содержится в другом на 80%+
    len1, len2 = len(norm1), len(norm2)
    min_len = min(len1, len2)
    max_len = max(len1, len2)

    if min_len / max_len > 0.8:
        # Проверяем, является ли один подстрокой другого
        if norm1 in norm2 or norm2 in norm1:
            return 1.0

    return 0

def extract_structured_content(html, url):
    """Извлечение структурированного контента"""
    soup = BeautifulSoup(html, 'html.parser')

    # Метаданные
    title = soup.find('title')
    title_text = clean_text(title.text) if title else "Untitled"

    meta_desc = soup.find('meta', attrs={'name': 'description'})
    description = clean_text(meta_desc.get('content', '')) if meta_desc else ""

    # Удаляем ненужные элементы
    for element in soup(['script', 'style', 'noscript', 'svg', 'iframe', 'nav']):
        element.decompose()

    # Удаляем header и footer более агрессивно
    for element in soup.find_all(['header', 'footer']):
        element.decompose()

    # Удаляем элементы с классами header/footer/menu
    for element in soup.find_all(class_=re.compile(r'header|footer|menu|nav', re.I)):
        element.decompose()

    # Находим основной контент
    # Для Tilda CMS сайтов используем body напрямую, так как контент в секциях по всей странице
    is_tilda = soup.find('div', class_=lambda x: x and ('tn-' in ' '.join(x) or 't396' in ' '.join(x)))

    if is_tilda:
        # Tilda - используем body
        main_content = soup.body or soup
    else:
        # Обычные сайты - ищем main контейнер
        main_content = (
            soup.find('main') or
            soup.find('article') or
            soup.find('div', id=re.compile(r'^content', re.I)) or
            soup.body or
            soup
        )

    # Структура контента
    content_structure = []
    seen_texts = set()  # Множество для отслеживания точных дубликатов

    def add_content(content_type, text, level=None):
        """Добавление контента с фильтрацией"""
        text = clean_text(text)

        # Фильтрация технического мусора
        if is_tech_noise(text):
            return

        # Минимальная длина (кроме заголовков)
        if content_type != 'heading' and len(text) < 10:
            return

        # Проверка на точные дубликаты (нормализованные)
        normalized = re.sub(r'\s+', ' ', text.lower()).strip()

        if normalized in seen_texts:
            return

        # Добавляем
        seen_texts.add(normalized)

        content_structure.append({
            'type': content_type,
            'text': text,
            'level': level
        })

    # Собираем контент
    # Сначала собираем заголовки
    for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        level = int(element.name[1])
        text = element.get_text()
        add_content('heading', text, level)

    # Затем параграфы
    for element in main_content.find_all('p'):
        text = element.get_text()
        add_content('paragraph', text)

    # Списки
    for element in main_content.find_all('li'):
        if not element.find_parent('li'):  # Только верхний уровень
            text = element.get_text()
            add_content('list_item', text)

    # Ищем текст в div'ах (особенно для Tilda CMS)
    # Tilda использует специфические классы для текстового контента
    tilda_text_classes = [
        'tn-atom',           # Текстовые блоки
        't-descr',           # Описания
        't491__content',     # Контент блоков
        't-card__descr',     # Описания карточек
        't-text',            # Текстовые блоки
        't-section__descr',  # Описания секций
    ]

    # Ищем div'ы с этими классами
    for class_name in tilda_text_classes:
        for element in main_content.find_all('div', class_=lambda x: x and class_name in x):
            # Пропускаем если внутри есть структурные элементы
            if element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol']):
                continue

            text = element.get_text(separator=' ', strip=True)

            if text and len(text) > 15:
                add_content('paragraph', text)

    # Дополнительно: ищем другие div'ы с текстом (если не Tilda)
    for element in main_content.find_all('div'):
        # Пропускаем уже обработанные Tilda элементы
        elem_classes = element.get('class', [])
        if any(tc in ' '.join(elem_classes) for tc in tilda_text_classes):
            continue

        # Пропускаем div'ы с заголовками внутри
        if element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol']):
            continue

        # Только если это "листовой" div с текстом (без много вложенных div'ов)
        child_divs = element.find_all('div')
        if len(child_divs) > 1:
            continue

        text = element.get_text(separator=' ', strip=True)

        if text and len(text) > 15:
            add_content('paragraph', text)

    return {
        'title': title_text,
        'url': url,
        'description': description,
        'content': content_structure
    }

def content_to_markdown(content_data):
    """Преобразование в markdown"""
    lines = []

    # Заголовок
    lines.append(f"# {content_data['title']}\n")
    lines.append(f"**URL:** {content_data['url']}\n")

    if content_data['description']:
        lines.append(f"**Description:** {content_data['description']}\n")

    lines.append("\n---\n")

    # Контент
    prev_type = None
    list_active = False

    for item in content_data['content']:
        content_type = item['type']
        text = item['text']

        if content_type == 'heading':
            level = item['level']
            if prev_type and prev_type != 'heading':
                lines.append("")
            lines.append(f"\n{'#' * level} {text}\n")
            list_active = False

        elif content_type == 'paragraph':
            if list_active:
                lines.append("")
                list_active = False
            lines.append(f"{text}\n")

        elif content_type == 'list_item':
            lines.append(f"- {text}")
            list_active = True

        prev_type = content_type

    # Очистка
    markdown = '\n'.join(lines)
    markdown = re.sub(r'\n{4,}', '\n\n\n', markdown)

    return markdown

def scrape_page_production(url):
    """Production скрейпинг"""
    print(f"Fetching: {url}")

    result = fetch_via_scrapedo(url)

    if not result['success']:
        print(f"  ✗ Error: {result['content']}")
        return None

    print("  Extracting content...")
    content_data = extract_structured_content(result['html'], url)

    print(f"  Found {len(content_data['content'])} elements")

    markdown = content_to_markdown(content_data)

    return markdown

def rescrape_all_pages():
    """Пересканировать все страницы с улучшенным скрейпером"""
    # Загружаем список страниц
    with open('site_structure.json', 'r', encoding='utf-8') as f:
        structure = json.load(f)

    # Создаем выходную директорию
    output_dir = Path('scraped_content_v2')
    output_dir.mkdir(exist_ok=True)

    results = []
    errors = []

    print(f"Rescaping {len(structure['pages'])} pages...\n")

    for i, page in enumerate(structure['pages'], 1):
        url = page['url']

        # Пропускаем non-HTTP URLs
        if not url.startswith('http'):
            print(f"[{i}/{len(structure['pages'])}] Skipping: {url}")
            continue

        print(f"[{i}/{len(structure['pages'])}] ", end='')

        try:
            markdown = scrape_page_production(url)

            if markdown:
                # Генерируем имя файла
                parsed_url = re.sub(r'https?://(www\.)?navicons\.com/?', '', url)
                filename = re.sub(r'[^\w\-_/]', '_', parsed_url)
                filename = re.sub(r'_+', '_', filename).strip('_')
                if not filename:
                    filename = 'index'
                filename += '.md'

                filepath = output_dir / filename

                # Создаем подпапки если нужно
                filepath.parent.mkdir(parents=True, exist_ok=True)

                filepath.write_text(markdown, encoding='utf-8')

                print(f"  ✓ Saved to {filename}")

                results.append({
                    'url': url,
                    'filename': filename,
                    'lines': len(markdown.split('\n'))
                })

                time.sleep(1.5)  # Rate limiting

        except Exception as e:
            error_msg = f"Failed: {str(e)}"
            print(f"  ✗ {error_msg}")
            errors.append({'url': url, 'error': error_msg})

    # Сохраняем summary
    summary = {
        'total_pages': len(structure['pages']),
        'successfully_scraped': len(results),
        'failed': len(errors),
        'pages': results,
        'errors': errors
    }

    with open('rescraping_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*70}")
    print(f"Rescraping complete!")
    print(f"Successfully: {len(results)}/{len(structure['pages'])}")
    print(f"Failed: {len(errors)}")
    print(f"Output: {output_dir.absolute()}")

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'all':
        rescrape_all_pages()
    else:
        # Тест на одной странице
        url = 'https://navicons.com/custom-development/'
        markdown = scrape_page_production(url)

        if markdown:
            output = 'custom-development-production.md'
            with open(output, 'w', encoding='utf-8') as f:
                f.write(markdown)

            print(f"\n✓ Saved to {output}")
            print(f"Total lines: {len(markdown.split(chr(10)))}")
