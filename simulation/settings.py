import json

def load_settings(filePath='simulation/settings.json'):
    with open(filePath, 'r') as f:
        return json.load(f)