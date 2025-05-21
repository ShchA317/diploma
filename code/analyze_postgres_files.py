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
        m = re.search(r'$(\d+)$', col_type)
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
        files[f"{name}_toast"] = create_file_entry(
            f"{name}_toast", toast_pages * PAGE_SIZE, "TOAST read/write", rps
        )
        row_size = 50

    rows_per_page = max(1, math.floor(PAGE_SIZE * FILL_FACTOR / row_size))
    total_pages = math.ceil(row_count / rows_per_page)

    files[name] = create_file_entry(
        name, total_pages * PAGE_SIZE, "Heap access (join read)" if is_joined else "Heap (unused)", rps
    )

    # Index storage
    index_bytes = row_count * 20
    files[f"{name}_{index_type}_index"] = create_file_entry(
        f"{name}_{index_type}_index", index_bytes, f"Index ({index_type})", rps
    )

    # FSM, VM, system
    files[f"{name}_fsm"] = create_file_entry(
        f"{name}_fsm", 16384, "Free Space Map", 0
    )

    files[f"{name}_vm"] = create_file_entry(
        f"{name}_vm", 16384, "Visibility Map", 0
    )

    return files

def create_file_entry(filename, size_bytes, access_type, rps):
    return {
        "filename": filename,
        "size_bytes": size_bytes,
        "rps": rps,
        "access_type": access_type
    }

def parse_query_for_tables(query):
    # Примитивный парсер JOIN
    tables = set()
    query = query.lower()
    matches = re.findall(r'from\s+(\w+)\s+\w+|join\s+(\w+)\s+\w+', query)
    for m in matches:
        tables.update(filter(None, m))
    return tables

def format_for_yaml(all_files):
    yaml_output = {
        "postgres_disk_io_prediction": {
            "database": "my_database",
            "tablespace": "pg_default",
            "files": []
        },
        "metadata": {
            "units": {
                "size": "MB",
                "throughput": "MB/s",
                "operations": "iops (read/write)"
            },
            "notes": [
                "cache_hit_ratio refers to percentage of data read from memory (not disk)",
                "Estimated throughput is approximate and hardware dependent",
                "FSM and VM files usually have much lower activity"
            ]
        }
    }

    for f in all_files:
        size_mb = round(f['size_bytes'] / (1024 * 1024), 3)
        file_entry = {
            "name": f['filename'],
            "type": f['access_type'].split()[0].lower(),
            "estimated_size_mb": size_mb,
            "access_pattern": {
                "total_operations": f['rps'] * 10,  # Example multiplier for demonstration
                "io_scenarios": generate_io_scenarios(f['rps'])
            }
        }
        yaml_output["postgres_disk_io_prediction"]["files"].append(file_entry)

    return yaml.dump(yaml_output, indent=2)

def generate_io_scenarios(rps):
    return [
        {"cache_hit_ratio": 0.0, "read_ops": int(rps * 0.6), "write_ops": int(rps * 0.4),
         "read_throughput_mb_s": 80, "write_throughput_mb_s": 40},
        {"cache_hit_ratio": 0.25, "read_ops": int(rps * 0.45), "write_ops": int(rps * 0.3),
         "read_throughput_mb_s": 60, "write_throughput_mb_s": 35},
        {"cache_hit_ratio": 0.5, "read_ops": int(rps * 0.3), "write_ops": int(rps * 0.2),
         "read_throughput_mb_s": 45, "write_throughput_mb_s": 30},
        {"cache_hit_ratio": "0.5-0.8", "read_ops": int(rps * 0.2), "write_ops": int(rps * 0.15),
         "read_throughput_mb_s": 30, "write_throughput_mb_s": 25}
    ]

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

    yaml_output = format_for_yaml(all_file_data)
    print(yaml_output)