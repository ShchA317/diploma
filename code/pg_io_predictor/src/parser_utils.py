import re

def parse_query_for_tables(query):
    tables = set()
    query = query.lower()
    matches = re.findall(r'from\s+(\w+)\s+\w+|join\s+(\w+)\s+\w+', query)
    for m in matches:
        tables.update(filter(None, m))
    return tables
