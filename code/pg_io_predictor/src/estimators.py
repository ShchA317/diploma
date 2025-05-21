import math
import re
from .constants import PAGE_SIZE, TOAST_THRESHOLD, FILL_FACTOR
from .file_model import create_file_entry
from .ddl_parser import extract_columns_from_ddl

def estimate_column_size(col_type):
    col_type = col_type.lower()
    if 'int' in col_type:
        return 4
    if 'bigint' in col_type:
        return 8
    if 'numeric' in col_type:
        return 16
    if 'timestamp' in col_type:
        return 8
    if 'varchar' in col_type or 'char' in col_type:
        m = re.search(r'\((\d+)\)', col_type)
        return int(m.group(1)) if m else 64
    if 'text' in col_type:
        return 2000
    if 'json' in col_type:
        return 3000
    return 32

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

    if toast_needed:
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

    index_bytes = row_count * 20
    files[f"{name}_{index_type}_index"] = create_file_entry(
        f"{name}_{index_type}_index", index_bytes, f"Index ({index_type})", rps
    )

    files[f"{name}_fsm"] = create_file_entry(f"{name}_fsm", 16384, "Free Space Map", 0)
    files[f"{name}_vm"] = create_file_entry(f"{name}_vm", 16384, "Visibility Map", 0)

    return files
