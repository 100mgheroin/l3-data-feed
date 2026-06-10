# Data Module Quick Guide

Краткая документация по запуску `data.__main__` и логике модулей `data.websocket` / `data.database`.

## Быстрый запуск

Запуск из корня проекта:

```bash
python -m data
```

Перед запуском создайте `.env` в корне проекта:

```env
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=postgres
```

Переменные окружения для подключения к БД:

- `DB_USER` (default: `postgres`)
- `DB_PASSWORD` (обязательная)
- `DB_HOST` (default: `127.0.0.1`)
- `DB_PORT` (default: `5432`)
- `DB_NAME` (default: `postgres`)

Альтернатива без `.env` (только на текущую сессию PowerShell):

```powershell
$env:DB_PASSWORD="your_password"
python -m data
```

Что делает запуск:

1. Создает `Database()` и подключается к Postgres.
2. Поднимает websocket-подключение к Bybit (`public/linear`).
3. Подписывается на:
   - `orderbook.50.<SYMBOL>`
   - `publicTrade.<SYMBOL>`
4. Буферизует данные и сохраняет их батчами в БД.

Точка входа: `__main__.py`.

## Модуль `database`

Основной класс: `Database` (`database/database.py`).

Ключевые методы:

- `connect(username, password, hostname, port, db_name)` — создает async engine и session maker, инициализирует таблицы.
- `_create_tables()` — `Base.metadata.create_all`.
- `clear_all_orderbooks()` — выполняет SQL из `queries/maintenance/truncate_orderbook.sql`.
- `save_orderbook_entry(data)` / `save_tradebook_entry(data)` — запись одной строки.
- `save_orderbook_batch(rows)` / `save_tradebook_batch(rows)` — быстрая batch-вставка через `insert(...)`.
- `disconnect()` — закрывает engine.

SQL хранится в `database/queries/**`, загрузка через `load_sql(name)`.

## Модуль `websocket`

Основной класс: `BybitDataCollector` (`websocket/bybit_ws_handler.py`).

Логика обработки:

- `on_ws_connected(...)` — отправляет subscribe-сообщение.
- `on_ws_frame(...)` — роутит входящие сообщения в async handlers:
  - `_handle_orderbook(msg)`
  - `_handle_trade(msg)`
- `_handle_orderbook(...)`:
  - поддерживает in-memory стакан (`asks`, `bids`),
  - считает L1 (`best_bid`, `best_ask`, `mid`, `spread`),
  - добавляет запись в `ob_buffer`,
  - при достижении `batch_size` сохраняет в БД.
- `_handle_trade(...)`:
  - нормализует трейды,
  - добавляет в `trade_buffer`,
  - при достижении `batch_size` сохраняет в БД.

## Поток данных (end-to-end)

`Bybit WS` -> `BybitDataCollector buffers` -> `Database.save_*_batch` -> `PostgreSQL tables`.

## Что импортировать

Через package exports:

```python
from database import Database
from websocket import BybitCollectorHandler
```
