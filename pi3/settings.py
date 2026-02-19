import json
import os

def load_settings(filePath='settings.json'):
    abs_path = filePath
    if not os.path.isabs(filePath):
        abs_path = os.path.join(os.getcwd(), filePath)
        if not os.path.exists(abs_path):
            abs_path = os.path.join(os.path.dirname(__file__), 'settings.json')

    with open(abs_path, 'r', encoding='utf-8') as f:
        return json.load(f)
