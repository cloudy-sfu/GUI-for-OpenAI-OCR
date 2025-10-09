import json
from operator import attrgetter

import jsonschema

with open("tests/json_schema/invalid_schema.json") as f:
    invalid_schema = json.load(f)
try:
    jsonschema.Draft7Validator.check_schema(invalid_schema)
except jsonschema.exceptions.SchemaError as e:
    path_str = "schema"
    for p in e.path:
        if isinstance(p, str):
            p_ = "\"" + p + "\""
        else:
            p_ = str(p)
        path_str += "[" + p_ + "]"
    print(f"At {path_str}, {e.message}.")


with open("tests/json_schema/user_profile.json") as f:
    user_profile = json.load(f)
try:
    jsonschema.Draft7Validator.check_schema(user_profile)
except jsonschema.exceptions.SchemaError as e:
    path_str = "schema"
    for p in e.path:
        if isinstance(p, str):
            p_ = "\"" + p + "\""
        else:
            p_ = str(p)
        path_str += "[" + p_ + "]"
    print(f"At {path_str}, {e.message}.")


validator = jsonschema.Draft7Validator(user_profile)
with open("tests/json_instance/valid_data.json") as f:
    valid_data = json.load(f)
errors = sorted(validator.iter_errors(valid_data), key=attrgetter('path'))
print(errors)
with open("tests/json_instance/invalid_data.json") as f:
    invalid_data = json.load(f)
errors = sorted(validator.iter_errors(invalid_data), key=attrgetter('path'))
for e in errors:
    path_str = "$"
    for p in e.path:
        if isinstance(p, str):
            p_ = "\"" + p + "\""
        else:
            p_ = str(p)
        path_str += "[" + p_ + "]"
    print(f"At {path_str}, {e.message}.")
