---
tags:
  - project/quantitative-finance
  - project-type/main
  - domain/quant-trading
  - domain/data-engineering
  - area/tasks
  - area/infra
  - area/market-data
  - topic/parser
  - topic/l3
  - integration/bybit
  - db/postgresql
  - stack/python
  - status/todo
---

ТЗ: доработать текущий Bybit-парсер (L2) до поддержки L3 в существующем pipeline.

## 1. Цель
- Обновить текущий data parser так, чтобы он умел собирать L3-данные Bybit и сохранять их в БД с тем же уровнем надежности, что и L2.
- Сохранить текущий рабочий флоу L2/L1 без регрессий.
---
## 2. Контекст
- Архитектурный ориентир: `[[connection_to_bybit]]`.
- Текущий код, который нужно доработать:
  - `data/websocket/collector/bybit.py`
  - `data/database/database.py`
  - `data/database/table/*`
  - `data/__main__.py` (только если нужно подключение новых флагов запуска)
---
## 3. Задача для исполнителя
Нужно не писать новый отдельный сервис, а обновить существующий parser слой:

1) Расширить WS collector в `data/websocket/collector/bybit.py`
- Добавить подписку на L3-топики Bybit (финальный список топиков зафиксировать в коде).
- Реализовать обработку L3 payload (нормализация полей, timestamp, symbol, side/price/size/sequence).
- Добавить отдельный буфер L3-сообщений по аналогии с текущими `ob_buffer` / `trade_buffer`.

2) Расширить persistence слой в `data/database/database.py`
- Добавить батч-метод сохранения L3 (`save_l3_batch`), аналогичный текущим `save_orderbook_batch` / `save_tradebook_batch`.
- Сохранить async-совместимость и batch insert подход.

3) Добавить/обновить DB-модель под L3
- Создать новую таблицу (или таблицы) в `data/database/table` для L3 событий.
- Поля минимум:
  - `ts`
  - `exchange_ts`
  - `symbol`
  - `side (side = 1, ask = 2)`
  - `price`
  - `size`
  - `action (add - 1, modify - 2, delete - 3)`
  - `update_id/sequence` (если есть в payload)
  - `raw_payload` (опционально)

4) Реализовать отказоустойчивость
- При сбое flush в БД — fallback запись в локальные файлы (`csv`/`npz`) в отдельную директорию.
- При восстановлении БД — возврат к штатной записи.
- Reconnect/backoff логика не должна ломать текущую обработку L2.
---
## 4. Scope

### In Scope
- Доработка существующего parser pipeline под L3.
- Расширение collector/database/table слоев.
- Логирование событий L3 ingestion (connect/reconnect/subscribe/flush/error).

### Out of Scope
- Торговая логика/ордер-менеджмент.
- Рефактор всех старых L2 таблиц.
- UI/дашборды.

## 5. Ограничения
- Не ломать текущий сбор L2 и tradebook.
- Не менять внешние контракты там, где это не требуется для L3.
- Изменения должны быть backward-compatible для текущего запуска.

## 6. Validation Plan
- Unit:
  - парсинг L3 payload
  - формирование L3 row
  - fallback writer
- Integration:
  - подключение к WS
  - запись L3 батча в БД
  - сценарий падения БД -> fallback
- Regression:
  - проверка, что L2 orderbook/tradebook продолжает писаться корректно

## 7. Acceptance Criteria
- [ ] Текущий parser собирает L3 и пишет в новую L3 таблицу(ы).
- [ ] L2 и tradebook продолжают работать без регрессий.
- [ ] При недоступности БД L3 данные сохраняются в локальные fallback-файлы.
- [ ] После восстановления БД запись снова идет в Postgres.
- [ ] Логи содержат отдельные события по L3 ingestion.

## 8. Deliverables
- [ ] Кодовые изменения в существующих файлах parser/database/table
- [ ] Модель(и) БД под L3
- [ ] Fallback механизм
- [ ] Краткий runbook: как запустить и как проверить L3

## 9. Notes
- Работать итеративно: сначала стабильный ingest/flush для L3, затем расширение полей.
- Не делать крупный рефактор архитектуры в рамках этой задачи.


### Также не забудь:
* Реализуй в yaml конфиге дата-фидера выбор принципа записи цены в таблицу (по тикам или по времени, 1 тик = 1 транзакция на бирже)