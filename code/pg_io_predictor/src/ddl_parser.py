import re
from .constants import INDEX_TYPES

def extract_columns_from_ddl(ddl):
    lines = ddl.strip().splitlines()
    cols = []
    index_type = 'btree'

    for line in lines:
        line = line.strip().strip(',')
        if line.upper().startswith("CREATE"):
            continue
        if 'key' in line.lower():
            for itype in INDEX_TYPES:
                if itype in line.lower():
                    index_type = itype
                    break
            continue
        match = re.match(r"(\w+)\s+([\w\(\),]+)", line)
        if match:
            col_name, col_type = match.groups()
            cols.append((col_name, col_type.strip()))
    return cols, index_type
