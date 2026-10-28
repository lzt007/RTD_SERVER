"""Read-only identity of the selected local database path, not its contents."""
import hashlib
import os
import pathlib


def database_path_id(path):
    canonical = os.path.normcase(str(pathlib.Path(path).resolve()))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
