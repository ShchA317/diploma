import re
from .constants import INDEX_TYPES

def extract_columns_and_indexes_from_ddl(ddl):
    cols = []
    indexes = []
    table_params = {}
    ddl = ddl.strip()
    lines = ddl.splitlines()
    in_cols = False
    table_name = None

    for line in lines:
        line = line.strip()
        if not line or line.startswith('--'): 
            continue
        if line.upper().startswith("CREATE TABLE"):
            in_cols = True
            m = re.match(r'CREATE TABLE\s+("?[\w\d_]+"?)', line, re.IGNORECASE)
            table_name = m.group(1).strip('"') if m else None
            continue
        if in_cols and line.startswith(')'):
            in_cols = False
            continue
        if in_cols:
            # колонки
            match = re.match(r'"?(\w+)"?\s+([a-zA-Z0-9$$, ]+)', line.rstrip(','))
            if match:
                col_name, col_type = match.groups()
                cols.append((col_name, col_type.strip()))
            continue
        # параметры таблицы (WITH (...))
        if line.upper().startswith("WITH"):
            params = re.findall(r'(\w+)\s*=\s*(\d+)', line)
            for k, v in params:
                table_params[k.lower()] = int(v)
            continue
        # индексы
        if line.upper().startswith("CREATE INDEX") or line.upper().startswith("CREATE UNIQUE INDEX"):
            unique = line.upper().startswith("CREATE UNIQUE INDEX")
            idx_type = 'btree'
            fillfactor = None
            idx_name_match = re.match(r'CREATE (?:UNIQUE )?INDEX\s+("?[\w\d_]+"?)', line, re.IGNORECASE)
            idx_name = idx_name_match.group(1).strip('"') if idx_name_match else None
            # попытка найти USING
            m = re.search(r'USING\s+(\w+)', line)
            if m:
                it = m.group(1).lower()
                if it in INDEX_TYPES:
                    idx_type = it
            # имя таблицы
            mtab = re.search(r'ON\s+("?[\w\d_]+"?)', line)
            # список колонок в скобках
            mcol = re.search(r'$([^)]+)$', line)
            colnames = []
            if mcol:
                colnames = [c.strip().strip('"') for c in mcol.group(1).split(',')]
            # fillfactor
            ff = re.search(r'fillfactor\s*=\s*(\d+)', line, re.IGNORECASE)
            if ff:
                fillfactor = int(ff.group(1))
            indexes.append({
                'name': idx_name or f'{table_name}_idx_{len(indexes)+1}',
                'columns': colnames,
                'type': idx_type,
                'unique': unique,
                'fillfactor': fillfactor,
            })
            
    return cols, indexes, table_params
