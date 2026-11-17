# Adrobot Campaign Console

Adrobot — небольшая операторская панель для тестирования работы с Keitaro. Backend написан на FastAPI + SQLAlchemy, frontend — на обычном HTML/CSS/JavaScript, поэтому для UI не нужен отдельный Node toolchain.

## Возможности

На экране **Создать кампанию** можно выбрать название, geo-коды, оффер, домен, группу и источник. Backend создаёт кампанию через Keitaro, затем создаёт два потока: geo-фильтр с redirect на Google и поток с выбранным оффером. На экране **Редактор кампании** можно выбрать кампанию, увидеть реальные ID, количество потоков и офферов, добавить оффер и удалить его из потоков кампании.

API-ключ Keitaro хранится только на backend. Если ключ не указан, приложение запускается в demo-состоянии: UI и health endpoint доступны, но операции, требующие Keitaro, возвращают понятное сообщение вместо попытки использовать тестовые данные.

## Локальный запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

В `.env` укажите:

```dotenv
DATABASE_URL=sqlite:///./adrobot.db
KEITARO_BASE_URL=https://tlgk.host
KEITARO_API_KEY=your_admin_api_key
DEMO_MODE=false
```

API-ключ можно создать в Keitaro: **Профиль → API ключи**. Приложение использует Admin API с заголовком `Api-Key` и базовым путём `/admin_api/v1`.

Примените миграции и запустите сервер:

```bash
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 3000
```

После запуска откройте `http://localhost:3000`. Проверка здоровья: `curl http://localhost:3000/health`.

## Конфигурация MySQL

Для managed или production database замените `DATABASE_URL` на DSN SQLAlchemy, например `mysql+pymysql://user:password@host/database`, и добавьте подходящий MySQL-драйвер в `requirements.txt`. Миграции остаются теми же: `alembic upgrade head`.

## API приложения

- `GET /api/config` — статус конфигурации без раскрытия ключа.
- `GET /api/catalog` — кампании, офферы, домены, группы и traffic sources.
- `POST /api/campaigns/create` — создаёт кампанию и два потока.
- `GET /api/campaigns/{id}` — возвращает кампанию, потоки и нормализованный список офферов.
- `POST /api/campaigns/{id}/offers` — добавляет оффер в поток кампании.
- `DELETE /api/campaigns/{id}/offers/{offer_id}` — удаляет оффер из потоков кампании.
- `GET /api/operations` — последние локальные записи журнала операций.

Пример создания кампании:

```bash
curl -X POST http://localhost:3000/api/campaigns/create \
  -H 'Content-Type: application/json' \
  -d '{"name":"Test RU","geo":["RU"],"offer_id":1,"domain_id":1,"group_id":1,"traffic_source_id":1}'
```

## Структура

`app/keitaro.py` содержит HTTP-клиент Keitaro и нормализацию, `app/routes.py` — публичный REST API, `app/models.py` — SQLAlchemy-модели журнала, `alembic/` — миграции, `app/static/` — интерфейс.

## Важное ограничение Keitaro

Офферы кампании являются частью конфигурации потоков. Поэтому редактор читает потоки кампании, а добавление и удаление оффера выполняет через `PUT /streams/{id}` с обновлённым массивом `offers`. Это позволяет сохранить корректные числовые показатели и фактическое состояние Keitaro.
