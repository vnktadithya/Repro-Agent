import tempfile
import os
import json
from pathlib import Path


def load_state(path: str) -> dict:
    # Returns the current state. If the file doesn't exist yet, 
    # returns an empty skeleton
    file_path = Path(path)

    if file_path.is_file():
        content = file_path.read_text(encoding="utf8")
        return json.loads(content)

    return {'cursor': None, 'next_page': 1, 'total_count': None, 'has_next_page': True, 'statuses': {}}

def save_state(state: dict, path: str) -> None:
    # Writes state to disk atomically
    dir_name = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_name)
    with os.fdopen(fd, 'w', encoding="utf8") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp_path, path)

def record_page(state, page_statuses, end_cursor, next_page, has_next_page, total_count, path):
    state['cursor'] = end_cursor
    state['next_page'] = next_page
    state['has_next_page'] = has_next_page
    state['total_count'] = total_count
    state['statuses'].update(page_statuses)

    save_state(state, path)