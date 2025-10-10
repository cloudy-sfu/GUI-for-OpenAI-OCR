import json
import os
import sys


class Config(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(sys, '_MEIPASS'):  # pyinstaller
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.abspath(".")
        os.makedirs(os.path.join(base_dir, "raw"), exist_ok=True)
        self.config_path = os.path.join(base_dir, "raw", "config.json")

        # schema
        self['openai_api_key'] = ""
        self['openai_model'] = ""
        self['max_retries'] = 3

        # load from file
        self.load()

    def dump(self):
        with open(self.config_path, "w") as g:
            json.dump(self, g, indent=4)

    def load(self):
        try:
            with open(self.config_path, "r") as f:
                config_ = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return
        self.update(config_)
