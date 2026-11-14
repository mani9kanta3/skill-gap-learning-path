"""
dictionary.py: internal consistency, and the decisions from ARCHITECTURE.md
that the schema has to carry.
"""

from pipeline import dictionary


def test_dictionary_is_consistent():
    assert dictionary.check_dictionary() == []


def test_table_lists():
    assert dictionary.INPUT_TABLES == (
        "department",
        "job_role",
        "skill",
        "role_skill_target",
        "employee",
        "course",
        "course_skill",
        "course_prerequisite",
        "course_offering",
        "budget",
        "recommendation",
        "enrollment",
        "enrollment_event",
        "completion",
        "proficiency_assessment",
        "employee_skill",
    )
    assert dictionary.EXPORTED_TABLES == dictionary.INPUT_TABLES + ("skill_gap",)
    assert dictionary.EVAL_TABLES == ("ground_truth", "detected_issue", "validation_result", "metric")


def test_every_table_has_a_primary_key():
    for table in dictionary.LOAD_ORDER:
        assert table.primary_key, table.name


def test_bridge_tables_use_composite_keys():
    for name in ("role_skill_target", "employee_skill", "course_skill", "course_prerequisite"):
        table = dictionary.table(name)
        assert table.kind == dictionary.BRIDGE
        assert len(table.primary_key) == 2


def test_no_retakes_is_enforced_as_unique_pairs():
    for name in ("recommendation", "enrollment"):
        assert ("employee_id", "course_id") in dictionary.table(name).unique


def test_duplicate_completions_can_be_loaded():
    # A duplicate completion is a labelled anomaly, so the database must
    # accept it and leave it to the validator.
    completion = dictionary.table("completion")
    assert all("enrollment_id" not in group for group in completion.unique)
    assert completion.primary_key == ("completion_id",)


def test_ground_truth_is_kept_out_of_the_input_schema():
    for name in dictionary.EVAL_TABLES:
        assert dictionary.table(name).schema == dictionary.EVAL
    for name in dictionary.EXPORTED_TABLES:
        table = dictionary.table(name)
        assert table.schema == dictionary.PUBLIC
        for column in table.column_names:
            for word in ("issue", "anomaly", "label", "ground_truth"):
                assert word not in column, f"{name}.{column}"


def test_plan_status_includes_every_rejection_reason():
    for reason in dictionary.NOT_RECOMMENDED_REASONS:
        assert reason in dictionary.PLAN_STATUS


def test_rule_codes_run_from_br01_to_br21():
    assert dictionary.RULE_CODES[0] == "BR-01"
    assert dictionary.RULE_CODES[-1] == "BR-21"
    assert len(dictionary.RULE_CODES) == 21


def test_unknown_table_is_an_error():
    try:
        dictionary.table("role")
    except KeyError as error:
        assert "role" in str(error)
    else:
        raise AssertionError("expected a KeyError")
