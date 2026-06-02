# Research Agent

AI-агент для академических исследований с поддержкой различных LLM, веб-поиска, парсинга и валидации научной литературы.

## Возможности

- 🤖 **Мульти-LLM поддержка**: OpenRouter и локальные модели (Ollama)
- 🔍 **Web Search**: Поиск по ключевым словам с перефразированием запросов
- 🌐 **Web Parser**: Скачивание и парсинг веб-страниц
- 💻 **Terminal Executor**: Безопасное выполнение команд
- 📄 **CV Instrument**: OCR для фото и отсканированных PDF
- 📚 **Research Skills**: Специализированные навыки для исследований
- ✅ **Literature Validation**: Проверка списков литературы и цитирований
- 🔬 **Scientific Databases**: Интеграция с arXiv, PubMed через MCP

## Технологический стек

- **Python 3.11+**
- **LangChain** — оркестрация агентов
- **OpenRouter API** — доступ к 100+ моделям
- **Ollama** — локальные LLM
- **Playwright** — продвинутый веб-парсинг
- **EasyOCR / Tesseract** — распознавание текста
- **MCP (Model Context Protocol)** — расширяемость

## Установка

```bash
git clone <repo-url>
cd research-agent
pip install -e ".[local,mcp,dev]"
playwright install
```

## Настройка

Создайте `.env` файл:
```env
OPENROUTER_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here  # опционально для локальных моделей
DEFAULT_MODEL=openai/gpt-4o
LOCAL_MODEL=llama3.1:8b
```

## Использование

```bash
# Запуск агента
research-agent run "Исследуй последние работы по RAG системам"

# Валидация литературы
research-agent validate --bibtex references.bib

# Веб-поиск
research-agent search "quantum computing" --rephrase
```

## Структура проекта

```
research-agent/
├── src/
│   ├── agents/          # Агенты LangChain
│   ├── tools/           # Инструменты (search, parser, etc.)
│   ├── models/          # Настройки LLM
│   ├── skills/          # Скиллы для ресерча
│   └── utils/           # Утилиты
├── config/              # Конфигурационные файлы
├── tests/               # Тесты
├── docs/                # Документация
└── skills/              # Пользовательские скиллы
```
