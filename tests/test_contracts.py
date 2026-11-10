import pytest
from jsonschema.exceptions import ValidationError

from tests.helpers import load_fixture, load_schema, make_validator, validate_instance

SCHEMAS = (
    "schema_slate.json",
    "schema_match.json",
    "schema_evolution.json",
    "schema_alert.json",
    "schema_blog.json",
    "schema_signal.json",
)

GOLDEN = (
    ("slate_empty.json", "schema_slate.json"),
    ("slate_one_match.json", "schema_slate.json"),
    ("match.json", "schema_match.json"),
    ("evolution.json", "schema_evolution.json"),
    ("alert.json", "schema_alert.json"),
    ("blog.json", "schema_blog.json"),
    ("signal.json", "schema_signal.json"),
)


@pytest.mark.parametrize("name", SCHEMAS)
def test_schema_files_are_valid(name):
    schema = load_schema(name)
    make_validator(schema)


@pytest.mark.parametrize("fixture_name,schema_name", GOLDEN)
def test_golden_instances_match_contracts(fixture_name, schema_name):
    validate_instance(load_fixture(fixture_name), schema_name)


def test_slate_rejects_unknown_field():
    instance = load_fixture("slate_empty.json")
    instance["nope"] = 1
    with pytest.raises(ValidationError):
        validate_instance(instance, "schema_slate.json")


def test_slate_rejects_bad_contract():
    instance = load_fixture("slate_empty.json")
    instance["contract"] = "vanus.slate.v0"
    with pytest.raises(ValidationError):
        validate_instance(instance, "schema_slate.json")


def test_slate_empty_matches_ok():
    instance = load_fixture("slate_empty.json")
    assert instance["matches"] == []
    validate_instance(instance, "schema_slate.json")


def test_match_null_index_is_a_hole():
    instance = load_fixture("match.json")
    assert instance["indexes"]["dailysportpick"] is None
    validate_instance(instance, "schema_match.json")


def test_alert_requires_two_agreeing():
    instance = load_fixture("alert.json")
    instance["agreeing"] = ["predictlix"]
    with pytest.raises(ValidationError):
        validate_instance(instance, "schema_alert.json")
