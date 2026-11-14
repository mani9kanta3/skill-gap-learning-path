"""
Writing and reading the dataset files, all driven by dictionary.py.

Byte-for-byte reproducibility depends on this file:
- rows are sorted by primary key before writing,
- every value is formatted from its declared SQL type (fixed decimals),
- CSV uses "\n" line endings and UTF-8 without a BOM,
- JSON uses sort_keys and a fixed indent,
- nothing here writes the time of day.
"""

import csv
import hashlib
import io
import json
from datetime import date
from pathlib import Path

from . import dictionary
from .ids import PATTERNS

# ---------------------------------------------------------------------------
# Value formatting
# ---------------------------------------------------------------------------


def _scale(sql_type):
    """NUMERIC(12,2) -> 2. None for anything that is not NUMERIC."""
    if sql_type.startswith("NUMERIC("):
        return int(sql_type[len("NUMERIC(") : -1].split(",")[1])
    return None


def to_text(value, column):
    """One value as it appears in CSV. None becomes an empty field."""
    if value is None:
        return ""
    t = column.sql_type
    if t == "DATE":
        return value.isoformat()
    if t in ("SMALLINT", "INTEGER"):
        return str(int(value))
    scale = _scale(t)
    if scale is not None:
        return f"{float(value):.{scale}f}"
    return str(value)


def from_text(text, column):
    """The reverse of to_text."""
    if text == "":
        return None
    t = column.sql_type
    if t == "DATE":
        return date.fromisoformat(text)
    if t in ("SMALLINT", "INTEGER"):
        return int(text)
    if _scale(t) is not None:
        return float(text)
    return text


def to_json_value(value, column):
    if value is None:
        return None
    t = column.sql_type
    if t == "DATE":
        return value.isoformat()
    if t in ("SMALLINT", "INTEGER"):
        return int(value)
    scale = _scale(t)
    if scale is not None:
        return round(float(value), scale)
    return value


def sorted_rows(table, rows):
    return sorted(rows, key=lambda r: tuple(r[k] for k in table.primary_key))


# ---------------------------------------------------------------------------
# CSV / JSON
# ---------------------------------------------------------------------------


def csv_text(table, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(table.column_names)
    for row in sorted_rows(table, rows):
        writer.writerow([to_text(row.get(col.name), col) for col in table.columns])
    return buffer.getvalue()


def json_text(table, rows):
    records = [
        {col.name: to_json_value(row.get(col.name), col) for col in table.columns}
        for row in sorted_rows(table, rows)
    ]
    # One record per line: still easy to read and diff, but about half the
    # size of an indented file, which matters at 40,000 rows.
    lines = [json.dumps(r, sort_keys=True, ensure_ascii=False, separators=(", ", ": ")) for r in records]
    return "[\n" + ",\n".join(lines) + ("\n" if lines else "") + "]\n"


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # newline="" so Python never turns "\n" into "\r\n" on Windows.
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def read_csv(table, path):
    """Rows of one CSV file, typed back from the dictionary."""
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        if tuple(header) != table.column_names:
            raise ValueError(f"{path}: columns {header} do not match the dictionary for {table.name}.")
        columns = table.columns
        return [{col.name: from_text(text, col) for col, text in zip(columns, line)} for line in reader]


def read_tables(csv_dir, names=dictionary.EXPORTED_TABLES):
    return {name: read_csv(dictionary.table(name), Path(csv_dir) / f"{name}.csv") for name in names}


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------


def _sql_literal(value, column):
    if value is None:
        return "NULL"
    text = to_text(value, column)
    t = column.sql_type
    if t in ("SMALLINT", "INTEGER") or _scale(t) is not None:
        return text
    return "'" + text.replace("'", "''") + "'"


def _quote_list(values):
    return ", ".join("'" + v.replace("'", "''") + "'" for v in values)


def schema_sql():
    """CREATE statements for every table, built from the dictionary."""
    lines = [
        "-- Generated from pipeline/dictionary.py. Do not edit by hand.",
        "CREATE SCHEMA IF NOT EXISTS eval;",
        "",
    ]
    for table in dictionary.LOAD_ORDER:
        parts = []
        for col in table.columns:
            parts.append(f"    {col.name} {col.sql_type}{' NOT NULL' if col.required else ''}")
        parts.append(f"    PRIMARY KEY ({', '.join(table.primary_key)})")
        for group in table.unique:
            parts.append(f"    UNIQUE ({', '.join(group)})")
        for col in table.columns:
            if col.enum is not None:
                parts.append(f"    CHECK ({col.name} IN ({_quote_list(col.enum)}))")
            if col.minimum is not None:
                parts.append(f"    CHECK ({col.name} >= {col.minimum})")
            if col.maximum is not None:
                parts.append(f"    CHECK ({col.name} <= {col.maximum})")
            if col.pattern is not None:
                parts.append(f"    CHECK ({col.name} ~ '{PATTERNS[col.pattern]}')")
        for col in table.columns:
            if col.references:
                target_table, _, target_column = col.references.partition(".")
                target = dictionary.table(target_table)
                parts.append(
                    f"    FOREIGN KEY ({col.name}) REFERENCES {target.schema}.{target_table} ({target_column}) "
                    "DEFERRABLE INITIALLY DEFERRED"
                )
        lines.append(f"CREATE TABLE IF NOT EXISTS {table.schema}.{table.name} (")
        lines.append(",\n".join(parts))
        lines.append(");")
        lines.append(f"COMMENT ON TABLE {table.schema}.{table.name} IS '{table.description.replace(chr(39), chr(39) * 2)}';")
        lines.append("")
    return "\n".join(lines)


def drop_sql():
    """DROP statements, children first."""
    return "\n".join(
        f"DROP TABLE IF EXISTS {t.schema}.{t.name} CASCADE;" for t in reversed(dictionary.LOAD_ORDER)
    ) + "\n"


def seed_sql(tables, batch=1000):
    """INSERTs for every table in load order, in one transaction."""
    out = [
        "-- Generated seed data. Load after schema.sql:  psql -f schema.sql -f seed.sql",
        "BEGIN;",
        "SET CONSTRAINTS ALL DEFERRED;",
        "",
    ]
    for table in dictionary.LOAD_ORDER:
        rows = sorted_rows(table, tables.get(table.name, []))
        if not rows:
            continue
        head = f"INSERT INTO {table.schema}.{table.name} ({', '.join(table.column_names)}) VALUES"
        for start in range(0, len(rows), batch):
            chunk = rows[start : start + batch]
            values = ",\n".join(
                "(" + ", ".join(_sql_literal(row.get(col.name), col) for col in table.columns) + ")"
                for row in chunk
            )
            out.append(f"{head}\n{values};")
        out.append("")
    out.append("COMMIT;")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Data dictionary document
# ---------------------------------------------------------------------------


def data_dictionary_md():
    lines = [
        "# Data dictionary",
        "",
        "Generated from `backend/pipeline/dictionary.py`, the single source for the schema,",
        "the SQL DDL and the validator's column checks. Do not edit by hand.",
        "",
        "Req = required (NOT NULL). Derived = recomputed from other rows in s10 and checked",
        "again by the validator. Formats are the regexes in `pipeline/ids.py`.",
        "",
    ]
    for table in dictionary.LOAD_ORDER:
        lines += [
            f"## {table.schema}.{table.name}",
            "",
            f"{table.description} Kind: {table.kind}. Primary key: `{', '.join(table.primary_key)}`.",
        ]
        if table.unique:
            lines.append("Unique: " + "; ".join(f"`{', '.join(g)}`" for g in table.unique) + ".")
        lines += ["", "| Column | Type | Req | Allowed values / rule | References | Derived |", "|---|---|---|---|---|---|"]
        for col in table.columns:
            rule = []
            if col.enum:
                rule.append(", ".join(col.enum))
            if col.minimum is not None or col.maximum is not None:
                low = "" if col.minimum is None else col.minimum
                high = "" if col.maximum is None else col.maximum
                rule.append(f"range {low}..{high}")
            if col.pattern:
                rule.append(f"`{PATTERNS[col.pattern]}`")
            if col.description:
                rule.append(col.description)
            lines.append(
                f"| {col.name} | {col.sql_type} | {'yes' if col.required else 'no'} | "
                f"{'; '.join(rule).replace('|', '/')} | {col.references or ''} | {'yes' if col.derived else ''} |"
            )
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Checksums
# ---------------------------------------------------------------------------


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def count_rows(path):
    """Data rows in a CSV (header excluded), records in a JSON array, else lines."""
    path = Path(path)
    if path.suffix == ".csv":
        with open(path, encoding="utf-8", newline="") as handle:
            return sum(1 for _ in csv.reader(handle)) - 1
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return len(data) if isinstance(data, list) else None
    with open(path, encoding="utf-8") as handle:
        return sum(1 for _ in handle)
