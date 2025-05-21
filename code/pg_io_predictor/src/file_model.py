def create_file_entry(filename, size_bytes, access_type, rps):
    return {
        "filename": filename,
        "size_bytes": size_bytes,
        "rps": rps,
        "access_type": access_type
    }
