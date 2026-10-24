import re
from pathlib import PurePosixPath
from .patches import OTHER_FOLDERS, TEST_FOLDERS, CONFIG_FILES, TEST_PATTERN

def decide_patch(file_path: str) -> str:

    folders = list(PurePosixPath(file_path).parts)
    root_folder = folders[0]
    file_name = folders[-1]

    if root_folder[0] != '.' and (any(folder in folders for folder in TEST_FOLDERS) or re.search(TEST_PATTERN, file_name) or file_name == 'conftest.py'):
        return 'test'

    elif root_folder[0] != '.' and not any(folder in folders for folder in OTHER_FOLDERS) and (file_name in CONFIG_FILES or PurePosixPath(file_name).suffix == '.py'):
        return 'source'

    else:
        return 'other'
