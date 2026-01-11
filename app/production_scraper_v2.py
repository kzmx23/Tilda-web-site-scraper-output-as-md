#!/usr/bin/env python3
"""
Production Web Scraper v2 with Accordion Support
- Tilda CMS support
- Accordion/collapsible content extraction
- Technical noise filtering
- Deduplication
"""

import sys
import json
import time
import re
from pathlib import Path
sys.path.insert(0, 'scrapedo-web-scraper/scripts')
from scrape import fetch_via_scrapedo
from bs4 import BeautifulSoup

# Technical noise patterns
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
    r'\{"lid":.+"li_nm"',
    r'\[{.+li_type.+}\]',
]

def is_tech_noise(text):
    """Check if text is technical noise"""
    if not text:
        return True

    text_clean = text.strip()

    if len(text_clean) < 3:
        return True

    for pattern in TECH_NOISE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True

    if re.match(r'^[\d\s\.,;:!?\-—]+$', text_clean):
        return True

    if re.match(r'^[a-z]+\s+[a-z/]+\s*$', text_clean, re.IGNORECASE):
        return True

    return False

def clean_text(text):
    """Clean text from extra whitespace"""
    if not text:
        return ""

    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    text = re.sub(r'&\w+;', '', text)
    text = re.sub(r'\s*=3D\s*', '', text)

    return text

def extract_accordion_content(soup):
    """Extract content from Tilda accordions (t585__accordion)"""
    accordion_content = []

    # Tilda accordions
    accordions = soup.find_all(attrs={'data-accordion': True})

    for acc in accordions:
        # Find title
        title_elem = acc.find(class_=lambda x: x and 'title' in str(x).lower())
        if title_elem:
            title = clean_text(title_elem.get_text())
            if title and not is_tech_noise(title):
                accordion_content.append({
                    'type': 'accordion_title',
                    'text': title
                })

        # Find content (usually hidden until expanded)
        content_elem = acc.find(class_=lambda x: x and ('content' in str(x).lower() or 'text' in str(x).lower() or 'descr' in str(x).lower()))
        if content_elem:
            content = clean_text(content_elem.get_text())
            if content and not is_tech_noise(content) and len(content) > 15:
                accordion_content.append({
                    'type': 'accordion_content',
                    'text': content
                })

    return accordion_content

def extract_structured_content(html, url):
    """Extract structured content including accordions"""
    soup = BeautifulSoup(html, 'html.parser')

    # Metadata
    title = soup.find('title')
    title_text = clean_text(title.text) if title else "Untitled"

    meta_desc = soup.find('meta', attrs={'name': 'description'})
    description = clean_text(meta_desc.get('content', '')) if meta_desc else ""

    # Remove unwanted elements
    for element in soup(['script', 'style', 'noscript', 'svg', 'iframe', 'nav']):
        element.decompose()

    for element in soup.find_all(['header', 'footer']):
        element.decompose()

    # Remove header/footer/menu/nav elements, but exclude Tilda-specific ones (like t585__header for accordions)
    for element in soup.find_all(class_=re.compile(r'header|footer|menu|nav', re.I)):
        classes = element.get('class', [])
        # Skip Tilda elements (those starting with 't' followed by digits)
        if not any(re.match(r'^t\d+__', cls) for cls in classes):
            element.decompose()

    # Detect Tilda
    is_tilda = soup.find('div', class_=lambda x: x and ('t396' in x or any('tn-' in cls for cls in x)))

    if is_tilda:
        main_content = soup.body or soup
    else:
        main_content = (
            soup.find('main') or
            soup.find('article') or
            soup.find('div', id=re.compile(r'^content', re.I)) or
            soup.body or
            soup
        )

    # Content structure
    content_structure = []
    seen_texts = set()

    def add_content(content_type, text, level=None):
        """Add content with deduplication"""
        text = clean_text(text)

        if is_tech_noise(text):
            return

        if content_type != 'heading' and content_type != 'accordion_title' and len(text) < 10:
            return

        normalized = re.sub(r'\s+', ' ', text.lower()).strip()

        if normalized in seen_texts:
            return

        seen_texts.add(normalized)

        content_structure.append({
            'type': content_type,
            'text': text,
            'level': level
        })

    # Extract accordion content FIRST (important!)
    accordion_items = extract_accordion_content(main_content)
    for item in accordion_items:
        add_content(item['type'], item['text'])

    # Collect headings
    for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        level = int(element.name[1])
        text = element.get_text()
        add_content('heading', text, level)

    # Collect paragraphs
    for element in main_content.find_all('p'):
        text = element.get_text()
        add_content('paragraph', text)

    # Collect list items
    for element in main_content.find_all('li'):
        if not element.find_parent('li'):
            text = element.get_text()
            add_content('list_item', text)

    # Tilda text classes
    tilda_text_classes = [
        'tn-atom',
        't-descr',
        't491__content',
        't-card__descr',
        't-text',
        't-section__descr',
    ]

    for class_name in tilda_text_classes:
        for element in main_content.find_all('div', class_=lambda x: x and class_name in x):
            if element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol']):
                continue

            text = element.get_text(separator=' ', strip=True)

            if text and len(text) > 15:
                add_content('paragraph', text)

    # Other divs
    for element in main_content.find_all('div'):
        elem_classes = element.get('class', [])
        if any(tc in ' '.join(elem_classes) for tc in tilda_text_classes):
            continue

        if element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol']):
            continue

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
    """Convert to markdown with accordion support"""
    lines = []

    # Header
    lines.append(f"# {content_data['title']}\n")
    lines.append(f"**URL:** {content_data['url']}\n")

    if content_data['description']:
        lines.append(f"**Description:** {content_data['description']}\n")

    lines.append("\n---\n")

    # Content
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

        elif content_type == 'accordion_title':
            # Accordion titles as level 3 headings with special marker
            if prev_type and prev_type != 'accordion_title':
                lines.append("")
            lines.append(f"\n### ➕ {text}\n")
            list_active = False

        elif content_type == 'accordion_content':
            lines.append(f"{text}\n")
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

    # Clean up
    markdown = '\n'.join(lines)
    markdown = re.sub(r'\n{4,}', '\n\n\n', markdown)

    return markdown

def scrape_page_v2(url):
    """Scrape page with accordion support"""
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

def rescrape_all_pages(structure_file='../utrace_structure.json', output_dir='../result/utrace/scraped_content'):
    """Rescrape all pages"""
    with open(structure_file, 'r', encoding='utf-8') as f:
        structure = json.load(f)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = []
    errors = []

    print(f"Scraping {len(structure['pages'])} pages...\n")

    for i, page in enumerate(structure['pages'], 1):
        url = page['url']

        if not url.startswith('http'):
            print(f"[{i}/{len(structure['pages'])}] Skipping: {url}")
            continue

        print(f"[{i}/{len(structure['pages'])}] ", end='')

        try:
            markdown = scrape_page_v2(url)

            if markdown:
                # Generate filename
                parsed_url = re.sub(r'https?://(www\.)?utrace\.ru/?', '', url)
                filename = re.sub(r'[^\w\-_/]', '_', parsed_url)
                filename = re.sub(r'_+', '_', filename).strip('_')
                if not filename:
                    filename = 'index'
                filename += '.md'

                filepath = output_path / filename
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(markdown, encoding='utf-8')

                print(f"  ✓ Saved to {filename}")

                results.append({
                    'url': url,
                    'filename': filename,
                    'lines': len(markdown.split('\n'))
                })

                time.sleep(1.5)

        except Exception as e:
            error_msg = f"Failed: {str(e)}"
            print(f"  ✗ {error_msg}")
            errors.append({'url': url, 'error': error_msg})

    # Save summary
    summary = {
        'total_pages': len(structure['pages']),
        'successfully_scraped': len(results),
        'failed': len(errors),
        'pages': results,
        'errors': errors
    }

    with open('../result/utrace/scraping_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*70}")
    print(f"Scraping complete!")
    print(f"Successfully: {len(results)}/{len(structure['pages'])}")
    print(f"Failed: {len(errors)}")
    print(f"Output: {output_path.absolute()}")

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'all':
        rescrape_all_pages()
    else:
        # Test on one page
        url = 'https://utrace.ru/utrace-hub'
        markdown = scrape_page_v2(url)

        if markdown:
            output = 'utrace-hub-test.md'
            with open(output, 'w', encoding='utf-8') as f:
                f.write(markdown)

            print(f"\n✓ Saved to {output}")
            print(f"Total lines: {len(markdown.split('\n'))}")
