import math
import re
from .constants import PAGE_SIZE, TOAST_THRESHOLD, FILL_FACTOR, DEFAULT_FILL_FACTOR, FSM_SIZE, VM_SIZE
from .file_model import create_file_entry
from .ddl_parser import extract_columns_and_indexes_from_ddl

def estimate_column_size_pg(col_type):
    c = col_type.lower()
    if 'int' in c and not 'big' in c:
        return 4
    if 'bigint' in c:
        return 8
    if 'smallint' in c:
        return 2
    if 'serial' in c or 'bigserial' in c:
        return 4 if 'big' not in c else 8
    if 'numeric' in c or 'decimal' in c:
        m = re.search(r'$(\d+),\s*(\d+)$', c)
        return 16 if m else 32
    if 'timestamp' in c or 'date' in c or 'time' in c:
        return 8
    if 'bool' in c:
        return 1
    if 'varchar' in c or 'char' in c:
        m = re.search(r'$(\d+)$', c)
        return int(m.group(1)) if m else 64
    if 'text' in c or 'json' in c or 'jsonb' in c or 'xml' in c or 'bytea' in c:
        # они потенциально TOASTable, но тут средний размер, реальный зависит от нагрузки
        return 3000
    return 32  # default size

def estimate_index_row_size(cols, index_type):
    if index_type in ['btree', 'gist', 'spgist', 'brin']:
        # индексная строка — примерно ключ + oid + overhead, но расчет упрощён;
        return sum(estimate_column_size_pg(col_type) for _, col_type in cols) + 8
    if index_type == 'gin':
        # GIN — мно-о-ого вспомогательных структур, обычно хранит ссылки и значения токенов
        return 64  # средняя оценка для полнотекстового или jsonb gin
    return 32

def estimate_table_storage(name, ddl, row_count, rps, is_joined):
    cols, indexes, params = extract_columns_and_indexes_from_ddl(ddl)
    row_overhead = 24  # header + xmin/xmax, oid, t_cid и др.
    row_size = row_overhead
    toastable_cols = []
    for cname, col_type in cols:
        col_size = estimate_column_size_pg(col_type)
        row_size += min(col_size, TOAST_THRESHOLD)
        # проверяем на TOAST
        if col_size >= TOAST_THRESHOLD or any(t in col_type.lower() for t in ['text', 'json', 'xml', 'bytea']):
            toastable_cols.append((cname, col_type, col_size))

    files = {}

    # HEAP/TABLE
    table_fill_factor = params.get('fillfactor', FILL_FACTOR)
    rows_per_page = max(1, math.floor(PAGE_SIZE * (table_fill_factor / 100) / row_size))
    total_table_pages = math.ceil(row_count / rows_per_page)
    files[name] = create_file_entry(
        name, total_table_pages * PAGE_SIZE, "Heap access (join read)" if is_joined else "Heap (unused)", rps
    )
    files[f"{name}_fsm"] = create_file_entry(f"{name}_fsm", FSM_SIZE(total_table_pages), "Free Space Map", 0)
    files[f"{name}_vm"] = create_file_entry(f"{name}_vm", VM_SIZE(total_table_pages), "Visibility Map", 0)
    files[f"{name}_init"] = create_file_entry(f"{name}_init", PAGE_SIZE, "Init fork", 0)

    # TOAST-файлы (таблицы и их индекс)
    if toastable_cols:
        # реальная структура более сложная, но — простая объёмная оценка
        avg_toasted = sum((c[2]-TOAST_THRESHOLD) for c in toastable_cols if c[2] > TOAST_THRESHOLD) / max(len(toastable_cols),1)
        toast_row_size = max(avg_toasted, 1000) + row_overhead
        toast_rows = row_count * len([c for c in toastable_cols if c[2] > TOAST_THRESHOLD])
        toast_pages = math.ceil(toast_rows * toast_row_size / (PAGE_SIZE * (table_fill_factor/100)))
        files[f"{name}_toast"] = create_file_entry(
            f"{name}_toast", toast_pages * PAGE_SIZE, "TOAST data", rps
        )
        # TOAST индекс — всегда btree
        index_rows = toast_rows
        index_row_size = 24  # btree on oid+chunk_id
        index_pages = math.ceil(index_rows * index_row_size / (PAGE_SIZE * (DEFAULT_FILL_FACTOR/100)))
        files[f"{name}_toast_index"] = create_file_entry(
            f"{name}_toast_index", index_pages * PAGE_SIZE, "TOAST index (btree)", rps
        )
        files[f"{name}_toast_fsm"] = create_file_entry(f"{name}_toast_fsm", FSM_SIZE(toast_pages), "TOAST FSM", 0)
        files[f"{name}_toast_vm"] = create_file_entry(f"{name}_toast_vm", VM_SIZE(toast_pages), "TOAST VM", 0)

    # Индексы (все, не только основной)
    for idx in indexes:
        idx_name = idx['name']
        idx_cols = [col for col in cols if col[0] in idx['columns']]
        idx_type = idx.get('type', 'btree').lower()
        unique_str = " (unique)" if idx.get('unique', False) else ""
        ind_fill_factor = idx.get('fillfactor', DEFAULT_FILL_FACTOR)
        index_row_size = estimate_index_row_size(idx_cols, idx_type)
        index_rows = row_count  # если уникальный и не partial, или меньше — если partial, фильтровать по idx
        # некоторые индексы (например, GIN по json) могут иметь гораздо больше строк, но это требует сложного анализа выражения
        index_pages = math.ceil(index_rows * index_row_size / (PAGE_SIZE * (ind_fill_factor / 100)))
        files[f"{name}_{idx_name}"] = create_file_entry(
            f"{name}_{idx_name}", index_pages * PAGE_SIZE, f"Index {idx_type}{unique_str}", rps
        )
        files[f"{name}_{idx_name}_fsm"] = create_file_entry(f"{name}_{idx_name}_fsm", FSM_SIZE(index_pages), f"Index {idx_type} FSM", 0)
        files[f"{name}_{idx_name}_vm"] = create_file_entry(f"{name}_{idx_name}_vm", VM_SIZE(index_pages), f"Index {idx_type} VM", 0)
        files[f"{name}_{idx_name}_init"] = create_file_entry(f"{name}_{idx_name}_init", PAGE_SIZE, f"Index {idx_type} INIT", 0)

    return files
