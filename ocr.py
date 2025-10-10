import json

from PyQt6.QtCore import QThread, pyqtSignal
from openai import OpenAI


class OCR(QThread):
    error_message = pyqtSignal(str, name='error_message')
    result = pyqtSignal(str, name='result')
    done = pyqtSignal(bool, name='done')

    def __init__(self, api_key, model_name, json_schema, data_url):
        super(OCR, self).__init__()
        self.api_key = api_key
        self.model_name = model_name
        self.data_url = data_url
        self.json_schema = json_schema
        # modify schema based on OpenAI special requirement
        self.json_schema["additionalProperties"] = False

    # noinspection PyTypeChecker
    def run(self) -> None:
        prompt = ("Perform OCR on this image and return data that strictly conforms to "
                  "the provided JSON schema.")
        try:
            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": self.data_url}}
                ]}],
                response_format={"type": "json_schema", "json_schema": {
                    "name": "schema_1",
                    "strict": True,
                    "schema": self.json_schema,
                }},
                reasoning_effort="minimal",
                temperature=0.2,
            )
            content = json.loads(response.choices[0].message.content)
            content = json.dumps(content, indent=4, ensure_ascii=False)
        except Exception as e:
            self.error_message.emit(str(e))
        else:
            self.result.emit(content)
            self.done.emit(True)
