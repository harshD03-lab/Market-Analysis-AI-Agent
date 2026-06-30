import yaml
from pathlib import Path
from typing import Dict, Any

class Config:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f'Configuration file not found: {self.config_path}')
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config

    def get(self, key: str, default=None) -> Any:
        return self.config.get(key, default)
