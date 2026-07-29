import json
import os
from typing import Dict, Any, overload
from app.core.paths import CONFIG_DIR
from app.core.config_defaults import DEFAULT_CONFIGS

class ConfigService:
    _instance = None
    _cache: Dict[str, Any] = {}
    
    CONFIG_DIR = CONFIG_DIR

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigService, cls).__new__(cls)
        return cls._instance

    def initialize(self):
        """Must be called after storage directories are ensured."""
        self.reload_all()

    def reload(self, domain: str):
        """Reload a specific configuration domain from disk."""
        self._cache[domain] = self._load_file(domain)

    def _deep_update(self, target_dict: dict, source_dict: dict):
        """Recursively update target_dict with values from source_dict."""
        for k, v in source_dict.items():
            if isinstance(v, dict) and k in target_dict and isinstance(target_dict[k], dict):
                self._deep_update(target_dict[k], v)
            else:
                target_dict[k] = v

    def reload_all(self):
        """Loads all core configs into memory."""
        print(f"Loading configurations from {self.CONFIG_DIR}...")
        
        # Ensure config directory exists
        os.makedirs(self.CONFIG_DIR, exist_ok=True)
        
        # Create missing defaults
        for name, default_data in DEFAULT_CONFIGS.items():
            path = os.path.join(self.CONFIG_DIR, f"{name}.json")
            if not os.path.exists(path):
                print(f"Creating default configuration: {name}.json")
                with open(path, "w", encoding='utf-8') as f:
                    json.dump(default_data, f, indent=4)
        
        # Load all configs
        loaded_count = 0
        for filename in os.listdir(self.CONFIG_DIR):
            if filename.endswith(".json"):
                name = filename[:-5]
                self._cache[name] = self._load_file(name)
                loaded_count += 1
                
        print(f"Successfully loaded {loaded_count} configurations.")

    def _load_file(self, name: str) -> Dict[str, Any]:
        path = os.path.join(self.CONFIG_DIR, f"{name}.json")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Merge with defaults to ensure new keys exist recursively
                if name in DEFAULT_CONFIGS:
                    import copy
                    default_data = copy.deepcopy(DEFAULT_CONFIGS[name])
                    self._deep_update(default_data, data)
                    return default_data
                return data
        except FileNotFoundError:
            default = DEFAULT_CONFIGS.get(name, {})
            with open(path, "w", encoding='utf-8') as f:
                json.dump(default, f, indent=4)
            return default
        except json.JSONDecodeError as e:
            print(f"CRITICAL: Invalid JSON in {name}.json: {e}")
            if os.path.exists(path):
                import shutil
                shutil.copy2(path, f"{path}.invalid")
            default = DEFAULT_CONFIGS.get(name, {})
            with open(path, "w", encoding='utf-8') as f:
                json.dump(default, f, indent=4)
            return default

    def get(self, path: str, subpath: Any = None, default: Any = None) -> Any:
        """
        Fetch a config value using dot notation. 
        Example: config.get("system.app.title", "Default Title")
        Example: config.get("system", "app.title", default="Default Title")
        config.get("ui") returns the full ui config dict.
        """
        if isinstance(subpath, str):
            path = f"{path}.{subpath}" if subpath else path
        elif subpath is not None:
            default = subpath

        parts = path.split('.')
        current = self._cache
        
        for part in parts:
            if not isinstance(current, dict):
                return default
            current = current.get(part)
            if current is None:
                return default
                
        return current
        
    def set(self, path: str, value: Any):
        """
        Set a config value using dot notation in cache only.
        Example: config.set("system.app.title", "New Title")
        """
        parts = path.split('.')
        if len(parts) == 1:
            self._cache[parts[0]] = value
            return
            
        current = self._cache
        for i, part in enumerate(parts[:-1]):
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
            
        current[parts[-1]] = value
        
    def save(self, domain: str, data: dict = None):
        """
        Save a specific domain back to its JSON file.
        If data is None, saves the current cache for that domain.
        """
        if data is not None:
            existing = self._cache.get(domain, {})
            self._deep_update(existing, data)
            self._cache[domain] = existing
            
        path = os.path.join(self.CONFIG_DIR, f"{domain}.json")
        try:
            # Create timestamped backup
            if os.path.exists(path):
                import shutil
                from datetime import datetime
                from app.core.paths import BACKUPS_DIR
                os.makedirs(BACKUPS_DIR, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(BACKUPS_DIR, f"{domain}_{timestamp}.json.bak")
                try:
                    shutil.copy2(path, backup_path)
                except Exception:
                    pass
                    
            # Atomic save
            import tempfile
            with tempfile.NamedTemporaryFile('w', dir=self.CONFIG_DIR, delete=False, encoding='utf-8') as f:
                json.dump(self._cache.get(domain, {}), f, indent=4)
                tmp_name = f.name
            os.replace(tmp_name, path)
        except Exception as e:
            print(f"Error saving {domain}.json: {e}")

# Initialize a global instance to be imported across the app
config = ConfigService()

