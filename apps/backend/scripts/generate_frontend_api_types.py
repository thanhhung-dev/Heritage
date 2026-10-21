"""Generate TypeScript API types from FastAPI's OpenAPI document.

Run from ``apps/frontend`` with the backend dependencies installed:

    npm run api:generate
    npm run api:check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "apps" / "frontend" / "types" / "api.generated.ts"


def _schema_type(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        return f'components["schemas"][{json.dumps(name)}]'

    for union_key in ("anyOf", "oneOf"):
        if union_key in schema:
            options = [_schema_type(item) for item in schema[union_key]]
            return " | ".join(dict.fromkeys(options)) or "unknown"

    if "allOf" in schema:
        options = [_schema_type(item) for item in schema["allOf"]]
        return " & ".join(options) or "unknown"

    if "enum" in schema:
        return " | ".join(json.dumps(value) for value in schema["enum"])

    schema_type = schema.get("type")
    if schema_type == "array":
        return f"Array<{_schema_type(schema.get('items', {}))}>"
    if schema_type == "object" or "properties" in schema:
        properties = schema.get("properties", {})
        if not properties:
            if schema.get("additionalProperties", True) is not False:
                additional = schema.get("additionalProperties", True)
                value_type = (
                    _schema_type(additional)
                    if isinstance(additional, dict)
                    else "unknown"
                )
                return f"Record<string, {value_type}>"
            return "Record<string, never>"

        required = set(schema.get("required", []))
        rows = []
        for name, field_schema in properties.items():
            optional = "" if name in required else "?"
            rows.append(
                f"    {json.dumps(name)}{optional}: {_schema_type(field_schema)};"
            )
        if schema.get("additionalProperties"):
            additional = schema["additionalProperties"]
            value_type = (
                _schema_type(additional)
                if isinstance(additional, dict)
                else "unknown"
            )
            rows.append(f"    [key: string]: {value_type};")
        return "{\n" + "\n".join(rows) + "\n  }"

    primitive_types = {
        "string": "string",
        "integer": "number",
        "number": "number",
        "boolean": "boolean",
        "null": "null",
    }
    return primitive_types.get(schema_type, "unknown")


def _content_schema(content: dict[str, Any]) -> str:
    json_content = content.get("application/json")
    if json_content is None:
        return "unknown"
    return _schema_type(json_content.get("schema", {}))


def _render_operation(operation: dict[str, Any]) -> str:
    rows: list[str] = []
    parameters = operation.get("parameters", [])
    grouped: dict[str, list[dict[str, Any]]] = {}
    for parameter in parameters:
        grouped.setdefault(parameter["in"], []).append(parameter)

    parameter_rows = []
    for location in ("path", "query", "header", "cookie"):
        entries = grouped.get(location, [])
        if not entries:
            continue
        fields = []
        for parameter in entries:
            name = parameter["name"]
            optional = "" if parameter.get("required") else "?"
            fields.append(
                f"        {json.dumps(name)}{optional}: "
                f"{_schema_type(parameter.get('schema', {}))};"
            )
        optional = "" if any(entry.get("required") for entry in entries) else "?"
        parameter_rows.append(
            f"      {json.dumps(location)}{optional}: {{\n"
            + "\n".join(fields)
            + "\n      };"
        )
    if parameter_rows:
        rows.append("    parameters: {\n" + "\n".join(parameter_rows) + "\n    };")

    request_body = operation.get("requestBody")
    if request_body:
        required = "" if request_body.get("required") else "?"
        required_flag = "required: true; " if request_body.get("required") else ""
        request_type = _content_schema(request_body.get("content", {}))
        rows.append(
            f"    requestBody{required}: {{ {required_flag}content: {{ "
            f'"application/json": {request_type} '
            "} };"
        )

    response_rows = []
    for status, response in operation.get("responses", {}).items():
        content = response.get("content")
        if content:
            response_type = _content_schema(content)
            response_rows.append(
                f"      {json.dumps(status)}: {{ content: {{ "
                f'"application/json": {response_type} '
                "} };"
            )
        else:
            response_rows.append(f"      {json.dumps(status)}: unknown;")
    rows.append("    responses: {\n" + "\n".join(response_rows) + "\n    };")
    return "  {\n" + "\n".join(rows) + "\n  }"


def render_types(spec: dict[str, Any]) -> str:
    schemas = spec.get("components", {}).get("schemas", {})
    schema_rows = []
    for name, schema in schemas.items():
        schema_rows.append(
            f"      {json.dumps(name)}: {_schema_type(schema)};"
        )

    path_rows = []
    for path, path_item in spec.get("paths", {}).items():
        method_rows = []
        for method, operation in path_item.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            operation_rows = _render_operation(operation).splitlines()
            method_rows.append(
                f"    {method.lower()}: {operation_rows[0]}\n"
                + "\n".join(f"  {row}" for row in operation_rows[1:-1])
                + f"\n    {operation_rows[-1]};"
            )
        path_rows.append(
            f"  {json.dumps(path)}: {{\n"
            + "\n".join(method_rows)
            + "\n  };"
        )

    generated = [
        "// Generated from the FastAPI OpenAPI contract. Do not edit by hand.",
        "// Regenerate with `npm run api:generate` from apps/frontend.",
        "",
        "export interface components {",
        "  schemas: {",
        *schema_rows,
        "  };",
        "}",
        "",
        "export interface paths {",
        *path_rows,
        "}",
        "",
    ]
    return "\n".join(generated)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the generated TypeScript file is out of date",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT))
    from apps.backend.app import app

    expected = render_types(app.openapi())
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
            print(
                "API contract types are out of date. "
                "Run `npm run api:generate` from apps/frontend.",
                file=sys.stderr,
            )
            return 1
        print("Generated API types match the FastAPI OpenAPI contract.")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(expected, encoding="utf-8", newline="\n")
    print(f"Generated {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
