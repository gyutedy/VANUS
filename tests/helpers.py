from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.validators import validator_for

from tests.conftest import CONTRACTS_DIR, FIXTURES_DIR


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_schema(name: str) -> dict:
    return load_json(CONTRACTS_DIR / name)


def load_fixture(name: str) -> dict:
    return load_json(FIXTURES_DIR / "json" / name)


def make_validator(schema: dict) -> Draft202012Validator:
    cls = validator_for(schema)
    cls.check_schema(schema)
    return cls(schema)


def validate_instance(instance: dict, schema_name: str) -> None:
    schema = load_schema(schema_name)
    make_validator(schema).validate(instance)
