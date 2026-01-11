

## General References

Always use python env to work with python (venv recommended)

## Web Scraping Best Practices

### Project Overview

**Scrapers available:**
- `production_scraper.py` (v1) - базовый скрейпер для обычных сайтов
- `production_scraper_v2.py` (v2) - расширенный скрейпер с поддержкой аккордеонов

### Environment Setup
```bash
# Always use virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install requests beautifulsoup4
```

### Tilda CMS Sites

**Detection**: Tilda sites use specific CSS classes

⚠️ **CRITICAL BUG FIX**: BeautifulSoup передает список классов напрямую в lambda, НЕ строку!

```python
# ✅ CORRECT (v2) - works with BeautifulSoup
is_tilda = soup.find('div', class_=lambda x: x and ('t396' in x or any('tn-' in cls for cls in x)))

# ❌ WRONG - doesn't work because BeautifulSoup doesn't join classes
is_tilda = soup.find('div', class_=lambda x: x and ('tn-' in ' '.join(x) or 't396' in ' '.join(x)))
```

**Why this matters**:
- BeautifulSoup's class_ parameter with lambda receives the class list directly
- Example: `['t396', 't396__artboard']` NOT `"t396 t396__artboard"`
- Checking `'tn-' in ' '.join(x)` returns False because 'tn-' is not in "t396 t396__artboard"
- Checking `'t396' in x` returns True because 't396' is in the list

**Content Extraction**: Use `body` directly for Tilda, not main/article containers
```python
if is_tilda:
    main_content = soup.body or soup  # Content is distributed across sections
else:
    main_content = soup.find('main') or soup.find('article') or soup.body
```

**Tilda Text Classes** to extract:
- `tn-atom` - text blocks
- `t-descr` - descriptions
- `t491__content` - block content
- `t-card__descr` - card descriptions
- `t-section__descr` - section descriptions

### Accordions (v2 Scraper)

**Accordions** - скрытые секции контента (collapsible content), которые раскрываются по клику на + или заголовок.

**Detection**:
```python
accordions = soup.find_all(attrs={'data-accordion': True})
# Tilda uses: <div class="t585__accordion" data-accordion="true">
```

**Structure**:
```python
def extract_accordion_content(soup):
    accordion_content = []
    accordions = soup.find_all(attrs={'data-accordion': True})

    for acc in accordions:
        # Title element - usually has 'title' in class name
        title_elem = acc.find(class_=lambda x: x and 'title' in str(x).lower())
        if title_elem:
            title = clean_text(title_elem.get_text())
            accordion_content.append({'type': 'accordion_title', 'text': title})

        # Content element - hidden until expanded
        content_elem = acc.find(class_=lambda x: x and ('content' in str(x).lower()
                                                         or 'text' in str(x).lower()
                                                         or 'descr' in str(x).lower()))
        if content_elem:
            content = clean_text(content_elem.get_text())
            accordion_content.append({'type': 'accordion_content', 'text': content})

    return accordion_content
```

**Markdown Output**:
- Accordion titles: `### ➕ Title`
- Accordion content: regular paragraph after title
- Symbol ➕ indicates expandable section

**Important**: Extract accordions BEFORE regular content to preserve correct order!

### Element Protection (Critical!)

⚠️ **CRITICAL BUG FIX**: Don't remove Tilda-specific elements when cleaning!

```python
# ✅ CORRECT (v2) - protect Tilda elements
for element in soup.find_all(class_=re.compile(r'header|footer|menu|nav', re.I)):
    classes = element.get('class', [])
    # Skip Tilda elements (those starting with 't' followed by digits)
    if not any(re.match(r'^t\d+__', cls) for cls in classes):
        element.decompose()

# ❌ WRONG - removes t585__header which contains accordion titles!
for element in soup.find_all(class_=re.compile(r'header|footer|menu|nav', re.I)):
    element.decompose()
```

**Why this matters**:
- `t585__header` contains accordion titles - critical content
- Tilda uses `t\d+__` pattern for component classes (t585__, t396__, etc.)
- Removing these breaks accordion extraction completely

### Content Cleaning

**Technical Noise Patterns** to filter:
```python
TECH_NOISE_PATTERNS = [
    r'nominify\s+(begin|end)',          # Tilda editor markers
    r'googleoff:.+googleon:',            # SEO directives
    r'\{"lid":.+"li_nm"',               # Form JSON data
    r'header\s*/header\s*footer',       # Template tags
]
```

**Elements to Remove**:
```python
for element in soup(['script', 'style', 'noscript', 'svg', 'iframe', 'nav', 'header', 'footer']):
    element.decompose()
```

### Deduplication Strategy

Use exact match on normalized text (lowercase, whitespace collapsed):
```python
normalized = re.sub(r'\s+', ' ', text.lower()).strip()
if normalized not in seen_texts:
    seen_texts.add(normalized)
    # Add content
```

**Avoid** similarity-based deduplication - too aggressive, loses content

### Content Structure

Collect in order:
1. Headings (h1-h6) with level tracking
2. Paragraphs (p tags)
3. List items (li tags, top-level only)
4. Div text (for Tilda - only leaf divs without structural elements)

### Rate Limiting

Always add delays for batch scraping:
```python
time.sleep(1.5)  # Between requests
```

### Common Issues

**Empty/Short Content**:
- Check if main_content container is correct
- Verify Tilda detection works
- Log container tag and classes for debugging

**Too Much Noise**:
- Add specific patterns to TECH_NOISE_PATTERNS
- Check element classes in browser DevTools
- Filter by minimum text length (>15 chars for paragraphs)

**Missing Content**:
- Tilda sites: content in divs, not p tags
- Check if classes match tilda_text_classes list
- Don't filter too aggressively

**Duplicates**:
- Use exact normalized matching, not similarity
- Track all seen texts in set
- Consider context (headings vs paragraphs)

## Project Results

### Company A.com (v1 scraper)
- **Status**: Completed ✅
- **Pages**: 38/45 (7 errors due to incorrect URLs)
- **Size**: 142 KB markdown
- **Lines**: 2,271 in global file
- **Format**: Structured MD files + global consolidated file

### Company B.ru (v2 scraper)
- **Status**: Completed ✅
- **Pages**: 22/24 (2 pages returned 404 - don't exist)
- **Size**: 382 KB markdown
- **Lines**: 2,814 in global file
- **Format**: Structured MD files + global consolidated file
- **Accordions**: 9+ per product page, all extracted successfully
- **Quality**: Average 150-250 lines per page with full content

## Key Lessons Learned

### 1. BeautifulSoup Lambda Behavior
BeautifulSoup passes class lists directly to lambda functions, not joined strings. Always check membership in the list, not in a joined string.

### 2. Tilda Element Protection
Tilda components use `t\d+__` naming pattern. These are NOT navigation elements - they're content containers. Protect them from removal.

### 3. Accordion Extraction Order
Extract accordions BEFORE regular content. Accordions often contain the most important information on product pages.

### 4. Exact Deduplication Only
Similarity-based deduplication (>0.8 threshold) removes too much valid content. Use exact normalized matching only.

### 5. Content Quality Metrics
- v1 (no accordions): ~65-127 lines per page
- v2 (with accordions): ~150-263 lines per page
- Accordions typically add 50-100 lines of valuable content per page

## Version Comparison

| Feature | v1 | v2 |
|---------|----|----|
| Tilda detection | Broken (lambda bug) | Fixed |
| Element protection | Missing | Implemented |
| Accordion support | No | Yes |
| Content quality | Medium | High |
| Average lines/page | ~100 | ~200 |
| Use case | Simple sites | Sites with hidden content |

## Commands

```bash
# Backend
cd backend && uv sync
uv run uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# Testing (Backend)
cd backend
uv run pytest tests/test_streak.py -v        # Unit tests
uv run pytest tests/ -v                       # All tests
uv run pytest --cov=app                       # With coverage

# Testing (Frontend)
npx playwright test                           # E2E tests
```

## MCP Servers

**Playwright MCP** is available for browser automation and E2E testing:
```bash
claude mcp add playwright npx @playwright/mcp@latest
```

Use Playwright MCP for:
- Running and debugging E2E tests
- Visual regression testing
- Browser automation tasks

## Reference Documentation

Read these documents when working on specific areas:

| Document | When to Read |
|----------|--------------|
| `.claude/PRD.md` | Understanding requirements, features, API spec |
| `.claude/reference/fastapi-best-practices.md` | Building API endpoints, Pydantic schemas, dependencies |
| `.claude/reference/sqlite-best-practices.md` | Database schema, queries, SQLAlchemy patterns |
| `.claude/reference/react-frontend-best-practices.md` | Components, hooks, state management, forms |
| `.claude/reference/testing-and-logging.md` | structlog setup, unit/integration/E2E testing patterns |
| `.claude/reference/deployment-best-practices.md` | Docker, production builds, deployment |

## Code Conventions

### Backend (Python)
- Use Pydantic models for all request/response schemas
- Separate schemas: `HabitCreate`, `HabitUpdate`, `HabitResponse`
- Use `Depends()` for database sessions and validation
- Store dates as ISO-8601 TEXT in SQLite (`YYYY-MM-DD`)
- Enable foreign keys via PRAGMA on every connection

### Frontend (React)
- Feature-based folder structure under `src/features/`
- Use TanStack Query for all API calls (no raw useEffect fetching)
- Tailwind CSS for styling - no separate CSS files
- Forms with react-hook-form + Zod validation

### API Design
- RESTful endpoints under `/api/`
- Return 201 for POST, 204 for DELETE
- Use HTTPException with descriptive error codes

## Logging

Use **structlog** for all logging. Configure at app startup:
- Development: Pretty console output with colors
- Production: JSON format for log aggregation

```python
import structlog
logger = structlog.get_logger()

# Bind context for all subsequent logs
structlog.contextvars.bind_contextvars(request_id=request_id)

# Log with structured data
logger.info("Habit completed", habit_id=1, streak=5)
```

Request logging middleware automatically logs:
- Request ID, method, path
- Response status code and duration

## Database

SQLite with WAL mode. Always run these PRAGMAs on connection:
```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA synchronous=NORMAL;
```

Two tables: `habits` and `completions`. See `.claude/PRD.md` for schema.

## Testing Strategy

### Testing Pyramid
- **70% Unit tests**: Pure functions, business logic, validators
- **20% Integration tests**: API endpoints with real database
- **10% E2E tests**: Critical user journeys with Playwright

### Unit Tests
- Test streak calculation, date utilities, validators
- Mock external dependencies
- Fast execution (milliseconds)

### Integration Tests
- Test API endpoints with in-memory SQLite
- Use `TestClient` and dependency overrides
- Test success and error cases

### E2E Tests
- Use Playwright with Page Object Model
- Test critical flows: create habit, complete habit, view calendar
- Run visual regression tests for UI consistency

### Test Organization
```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   └── test_streak.py       # Business logic tests
├── integration/
│   └── test_api_habits.py   # API tests with real DB
└── e2e/
    ├── pages/               # Page objects
    └── habits.spec.js       # User journey tests
```
