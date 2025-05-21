from .estimators import estimate_table_storage
from .output_formatter import format_for_yaml
from .parser_utils import parse_query_for_tables

def run_prediction(config):
    joined_tables = parse_query_for_tables(config['load_generator']['query'])
    rps = config['load_generator']['rps']
    all_file_data = []

    for table in config['tables']:
        name = table['name']
        is_joined = name.lower() in joined_tables
        files = estimate_table_storage(name, table['ddl'], table['row_count'], rps, is_joined)
        all_file_data.extend(files.values())

    return format_for_yaml(all_file_data)
