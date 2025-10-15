import base64
import io
import json
import os

from PIL import Image
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
        make_all_fields_required(self.json_schema)

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
            )
            content = json.loads(response.choices[0].message.content)
            content = json.dumps(content, indent=4, ensure_ascii=False)
        except Exception as e:
            self.error_message.emit(str(e))
        else:
            self.result.emit(content)
        self.done.emit(True)


class BatchOCR(QThread):
    progress = pyqtSignal(int, name='progress')
    gui_message = pyqtSignal(str, name="gui_message")
    done = pyqtSignal(bool, name='done')

    def __init__(self, api_key, model_name, json_schema, input_folder, output_folder):
        super(BatchOCR, self).__init__()
        self.api_key = api_key
        self.model_name = model_name
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.json_schema = json_schema
        make_all_fields_required(self.json_schema)

    # noinspection PyTypeChecker
    def run(self) -> None:
        filenames = []
        for parent, _, files in os.walk(self.input_folder):
            filenames += [(parent, x) for x in files if
                          os.path.splitext(x)[1].lower() in ('.jpg', '.png', '.jpeg')]
        n_files = len(filenames)
        if n_files == 0:
            self.gui_message.emit('This folder doesn\'t contains any picture.')
            self.done.emit(True)
            return
        try:
            client = OpenAI(api_key=self.api_key)
        except Exception as e:
            self.gui_message.emit(str(e))
            self.done.emit(True)
            return
        prompt = ("Perform OCR on this image and return data that strictly conforms to "
                  "the provided JSON schema.")
        # batch logic
        for i, (parent, name) in zip(range(n_files), filenames):
            input_path = os.path.join(parent, name)
            output_image_name, output_image_ext = os.path.splitext(name)
            output_path = os.path.join(
                self.output_folder, output_image_name + '.json')
            # OCR
            try:
                with Image.open(input_path) as img:
                    fmt = (img.format or "PNG").upper()
                    mime = f"image/{'jpeg' if fmt == 'JPEG' else fmt.lower()}"
                    buf = io.BytesIO()
                    img.save(buf, format=fmt)
                    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                    data_url = f"data:{mime};base64,{b64}"
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}}
                    ]}],
                    response_format={"type": "json_schema", "json_schema": {
                        "name": "schema_1",
                        "schema": self.json_schema,
                    }},
                    reasoning_effort="minimal",
                )
                content = json.loads(response.choices[0].message.content)
            except Exception as e:
                self.gui_message.emit(f"{input_path} - {e}")
            else:
                with open(output_path, 'w') as f:
                    json.dump(content, f, indent=4, ensure_ascii=False)
            progress_percentage = int((i + 1) / n_files * 100)
            self.progress.emit(progress_percentage)
        os.startfile(self.output_folder)
        self.done.emit(True)


def make_all_fields_required(schema):
    """
    Recursively traverses a JSON schema and makes all fields required.
    Modifies the schema in-place.
    """
    if isinstance(schema, dict):
        # If 'properties' exists, make all of them required
        if 'properties' in schema and isinstance(schema['properties'], dict):
            already_required = set(schema.get('required', []))
            schema['required'] = list(schema['properties'].keys())
            for field_name, child in schema['properties'].items():
                if (field_name not in already_required) and ('type' in child.keys()):
                    if isinstance(child['type'], str):
                        child['type'] = [child['type'], "null"]
                    elif "null" not in child['type']:  # child['type'] is list
                        child['type'].append("null")
            schema['additionalProperties'] = False
        # Recursively process all values in the dictionary
        for key, value in schema.items():
            make_all_fields_required(value)
    elif isinstance(schema, list):
        # If it's a list, process each item in the list
        for item in schema:
            make_all_fields_required(item)
