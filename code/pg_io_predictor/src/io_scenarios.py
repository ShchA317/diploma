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
