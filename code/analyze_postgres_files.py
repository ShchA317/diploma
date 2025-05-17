import yaml
import math
import re
import argparse

PAGE_SIZE = 8192
TOAST_THRESHOLD = 2000
FILL_FACTOR = 0.85

INDEX_TYPES = ['btree', 'hash', 'gin', 'gist', 'spgist', 'brin']

def estimate_column_size(col_type):
    col_type = col_type.lower()
    if 'int' in col_type:
        return 4
    if 'numeric' in col_type:
        return 16
    if 'timestamp' in col_type:
        return 8
    if 'char' in col_type:
        m = re.search(r'\((\d+)\)', col_type)
        return int(m.group(1)) if m else 64
    if 'text' in col_type:
        return 2000
    if 'json' in col_type:
        return 3000
    return 32

def extract_columns_from_ddl(ddl):
    lines = ddl.strip().splitlines()
    cols = []
    index_type = 'btree'
    for line in lines:
        if line.strip().startswith("CREATE"):
            continue
        line = line.strip().strip(',').strip()
        if line.lower().startswith("primary key") or "key" in line.lower():
            if 'gin' in line.lower(): index_type = 'gin'
            elif 'gist' in line.lower(): index_type = 'gist'
            elif 'hash' in line.lower(): index_type = 'hash'
            elif 'brin' in line.lower(): index_type = 'brin'
            elif 'spgist' in line.lower(): index_type = 'spgist'
        parts = line.split()
        if len(parts) >= 2:
            col_name = parts[0]
            col_type = parts[1]
            cols.append((col_name, col_type))
    return cols, index_type

def estimate_table_storage(name, ddl, row_count, rps, is_joined):
    columns, index_type = extract_columns_from_ddl(ddl)

    row_size = 24
    toast_needed = False
    for _, col_type in columns:
        col_size = estimate_column_size(col_type)
        row_size += col_size
        if col_size >= TOAST_THRESHOLD:
            toast_needed = True

    files = {}

    if row_size >= TOAST_THRESHOLD:
        toast_pages = math.ceil(row_count * row_size / (PAGE_SIZE * FILL_FACTOR))
        files[f"{name}_toast"] = {
            "filename": f"{name}_toast",
            "size_bytes": toast_pages * PAGE_SIZE,
            "rps": rps if is_joined else 0,
            "access_type": "TOAST read/write"
        }
        row_size = 50

    rows_per_page = max(1, math.floor(PAGE_SIZE * FILL_FACTOR / row_size))
    total_pages = math.ceil(row_count / rows_per_page)

    files[name] = {
        "filename": name,
        "size_bytes": total_pages * PAGE_SIZE,
        "rps": rps if is_joined else 0,
        "access_type": "Heap access (join read)" if is_joined else "Heap (unused)"
    }

    # Index storage
    index_bytes = row_count * 20
    files[f"{name}_{index_type}_index"] = {
        "filename": f"{name}_{index_type}_index",
        "size_bytes": index_bytes,
        "rps": rps if is_joined else 0,
        "access_type": f"Index ({index_type})"
    }

    # FSM, VM, system
    files[f"{name}_fsm"] = {
        "filename": f"{name}_fsm",
        "size_bytes": 16384,
        "rps": 0,
        "access_type": "Free Space Map"
    }

    files[f"{name}_vm"] = {
        "filename": f"{name}_vm",
        "size_bytes": 16384,
        "rps": 0,
        "access_type": "Visibility Map"
    }

    return files

def parse_query_for_tables(query):
    # Примитивный парсер JOIN
    tables = set()
    query = query.lower()
    matches = re.findall(r'from\s+(\w+)\s+\w+|join\s+(\w+)\s+\w+', query)
    for m in matches:
        tables.update(filter(None, m))
    return tables

def print_results(all_files):
    print(f"{'File':<30} {'Size (KB)':<15} {'RPS':<10} {'Access Type'}")
    print("-" * 80)
    for f in all_files:
        kb = f['size_bytes'] / 1024
        print(f"{f['filename']:<30} {kb:<15.1f} {f['rps']:<10} {f['access_type']}")

if __name__ == "__main__":
    # Добавлен парсер аргументов
    parser = argparse.ArgumentParser(description="PostgreSQL storage analyzer")
    parser.add_argument("config", help="Path to YAML config file", default="config.yaml", nargs='?')
    args = parser.parse_args()

    try:
        with open(args.config, "r") as f:
            config = yaml.safe_load(f)['load_prediction_config']
    except FileNotFoundError:
        print(f"Error: Config file '{args.config}' not found!")
        exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        exit(1)

    joined_tables = parse_query_for_tables(config['load_generator']['query'])
    rps = config['load_generator']['rps']

    all_file_data = []

    for table in config['tables']:
        name = table['name']
        is_joined = name.lower() in joined_tables
        files = estimate_table_storage(name, table['ddl'], table['row_count'], rps, is_joined)
        all_file_data.extend(files.values())

    print_results(all_file_data)