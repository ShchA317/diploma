import re
import math
import sqlglot

DEFAULT_BLOCK_SIZE = 8192  # 8KB
DEFAULT_SEGMENT_SIZE = 1 * 1024 * 1024 * 1024  # 1GB

# Оценочный размер типов
TYPE_SIZE_MAP = {
    'integer': 4,
    'int': 4,
    'bigint': 8,
    'smallint': 2,
    'serial': 4,
    'bigserial': 8,
    'text': 100,  # оценка
    'varchar': 50,
    'character varying': 50,
    'date': 4,
    'timestamp': 8,
    'boolean': 1,
    'uuid': 16,
    'json': 200,
    'jsonb': 200
}

def parse_column_types(ddl: str) -> dict:
    parsed = sqlglot.parse_one(ddl, read='postgres')
    if parsed is None or parsed.args.get('expressions') is None:
        raise ValueError("Невалидный DDL")

    columns = {}
    for column in parsed.args['expressions']:
        if column.args.get("kind") != "column":
            continue
        name = column.name
        type_str = str(column.args["datatype"]).lower()
        base_type = re.sub(r'\(.*\)', '', type_str).strip()
        columns[name] = TYPE_SIZE_MAP.get(base_type, 100)  # по умолчанию 100 байт
    return columns

def estimate_row_size(columns: dict) -> int:
    return sum(columns.values()) + 24  # 24 байта накладные расходы PostgreSQL

def estimate_table_size(row_size: int, row_count: int, block_size=DEFAULT_BLOCK_SIZE) -> int:
    total_size = row_size * row_count
    return total_size

def calculate_file_segments(total_size: int, segment_size=DEFAULT_SEGMENT_SIZE) -> list:
    num_segments = math.ceil(total_size / segment_size)
    file_names = [f"{'base/oid/relfilenode'}.{i}" if i > 0 else "base/oid/relfilenode"
                  for i in range(num_segments)]
    file_sizes = [min(segment_size, total_size - i * segment_size) for i in range(num_segments)]
    return list(zip(file_names, file_sizes))

def main(ddl: str, row_count: int, block_size=DEFAULT_BLOCK_SIZE, segment_size=DEFAULT_SEGMENT_SIZE):
    print("🔍 Проверка синтаксиса и парсинг колонок...")
    columns = parse_column_types(ddl)
    row_size = estimate_row_size(columns)
    print(f"📏 Размер одной строки: {row_size} байт")
    
    total_size = estimate_table_size(row_size, row_count, block_size)
    print(f"📦 Общий размер данных: {total_size} байт")

    segments = calculate_file_segments(total_size, segment_size)
    print(f"📂 Файлы хранения:")
    for name, size in segments:
        print(f" - {name} : {size / (1024*1024):.2f} MB")

    return segments

# Пример использования
if __name__ == "__main__":
    example_ddl = """
    CREATE TABLE users (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100),
        email TEXT,
        created_at TIMESTAMP
    );
    """
    row_count = 1_000_000
    main(example_ddl, row_count)
