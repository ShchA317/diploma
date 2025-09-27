# 🔍 PostgreSQL disk Load Analyzer
Автоматизированная система предсказания нагрузки на диск PostgreSQL.
Подходит для моделирования нагрузки, оценки размеров файлов БД, активности WAL и индексов — с возможностью учитывать как INSERT, так и SELECT/JOIN-нагрузку.

### 📦 Возможности

- 📑 Парсинг DDL SQL-таблиц и нагрузочных SQL-запросов
- 🧮 Оценка размеров файлов хранения (heap, TOAST, индексы, FSM, VM)
- 💾 Анализ нагрузок типа SELECT, INSERT, JOIN
- 🔁 Учёт WAL, автогенерация статистики по доступам к каждому файлу
- 📊 Поддержка GIN, BRIN, B-Tree, Hash и других индексов
- 🔧 Конфигурация через YAML (читаемая и расширяемая)
- ✅ Интеграция с GitHub Actions (CI)

### 📁 Пример YAML-конфигурации

```yaml
load_prediction_config:
  tables:
    - name: logs
      ddl: |
        CREATE TABLE logs (
          id BIGSERIAL PRIMARY KEY,
          message TEXT,
          metadata JSONB
        );
      row_count: 0

load_generator:
  query: |
    INSERT INTO logs (message, metadata)
    VALUES ('test', '{"event": "login"}');
  rps: 1500

postgresql_config:
  wal_level: "replica"
  shared_buffers: "2GB"

environment:
  cpu_cores: 4
  ram_gb: 16
```

🚀 Быстрый старт
📦 Установите зависимости:

```bash
pip install -r requirements.txt
```

🧪 Запустите анализ по YAML-файлу:

```bash
python analyze_multitable_postgres.py examples/example1.yaml
```

## ⚙️ GitHub Actions

Файл CI/CD уже настроен в .github/workflows/test.yaml:

проверяет примеры YAML (examples/*.yaml)

выводит прогон логики анализа в терминал

## 📁 Структура проекта

```
.
├── analyze_postgres_files.py # Главный скрипт анализа
├── examples/ # Примеры YAML-файлов
│ └── example1.yaml
| └── ...
| └── exampleN.yaml
├── requirements.txt
└── .github/workflows/test.yaml # GitHub Actions CI
```

## 🧠 Поддерживаемые типы анализа

| Тип          | Поддержка       | Детали                                  |
|:--------------:|:-----------------:|:-----------------------------------------:|
| SELECT       | ✅ Полная       | Оценка heap, индексов, TOAST            |
| INSERT       | ✅ Полная       | WAL, FSM, VM, индексные записи         |
| JOIN         | ✅ Полная       | Анализ обращений ко всем таблицам       |
| UPDATE/DELETE| ⚠️ Не поддерживается | -                                  |
| Индексы      | ✅ Полная       | B-Tree, GIN, BRIN, Hash                 |
| TOAST        | ✅ Полная       | Автоопределение и анализ                |
| WAL          | ⚠️ Частичная    | Размер и обращение при записи           |
| AUTOVACUUM   | ⚠️ Не оддерживается | -                                  |

### 📜 Лицензия
MIT License. Проект открыт для использования в учебных и исследовательских целях.

