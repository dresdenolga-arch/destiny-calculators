# Разбор по дате рождения

FastAPI-сайт поверх трёх готовых расчётных движков: Матрица судьбы (нумерология),
Ба-цзы (китайская астрология), Джйотиш (ведическая астрология).

## Структура

- `engine/matrix`, `engine/bazi`, `engine/jyotish` — копии расчётных скриптов и
  справочников из скиллов `~/.codex/skills/*`. Логика расчёта не менялась.
- `app/services/*.py` — обёртка API над движками: `matrix_service.py` вызывает
  `calculate.py`/`render_html.py` напрямую как модуль, `bazi_service.py` и
  `jyotish_service.py` запускают свои скрипты подпроцессом и парсят JSON из stdout.
- `app/main.py` — FastAPI-приложение: `/api/matrix`, `/api/matrix/html`,
  `/api/bazi`, `/api/jyotish`.
- `app/static/` — простой фронтенд (без сборки): форма на три вкладки + вывод
  результата JSON в читаемом виде.

## Запуск

```bash
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Открыть http://localhost:8000

Либо через Claude Code preview: `.claude/launch.json` уже настроен
(`preview_start` с именем `birthdate-sites`).

## Статус движков

- **Матрица судьбы** — полностью рабочая, без внешних зависимостей.
- **Ба-цзы** — рабочий, зависит от чистого Python-пакета `lunar_python`
  (уже в requirements.txt).
- **Джйотиш** — код готов, но не запустится без пакета `pyswisseph`. На Windows
  под эту версию Python нет готового wheel — нужен компилятор
  (Microsoft C++ Build Tools), чтобы собрать пакет из исходников. До тех пор
  `/api/jyotish` возвращает понятную ошибку 400 с объяснением.

## Что дальше (не сделано)

- Установка Microsoft C++ Build Tools + `pyswisseph`, если нужен Джйотиш.
- Деплой (сейчас только локальный запуск).
- Более богатый фронтенд под конкретный бренд/дизайн вместо технической
  JSON-раскладки.
