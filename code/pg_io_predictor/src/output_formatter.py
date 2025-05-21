import yaml
from .io_scenarios import generate_io_scenarios

def format_for_yaml(all_files):
    result = {
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
                "cache_hit_ratio: % of reads served from memory",
                "TOAST storage is only used for large fields",
                "FSM and VM are mostly idle"
            ]
        }
    }

    for f in all_files:
        size_mb = round(f['size_bytes'] / (1024 * 1024), 3)
        result["postgres_disk_io_prediction"]["files"].append({
            "name": f['filename'],
            "type": f['access_type'].split()[0].lower(),
            "estimated_size_mb": size_mb,
            "access_pattern": {
                "total_operations": f['rps'] * 10,
                "io_scenarios": generate_io_scenarios(f['rps'])
            }
        })

    return yaml.dump(result, indent=2)
