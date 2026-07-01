"""Gerador de dados de exemplo (payloads) para os endpoints.

Implementa ``IExampleDataGenerator``. Consolida a lógica que vivia no
``step3_dados_exemplo.py``, delegando a geração via LLM para um ``ILlmClient``
injetado (inversão de dependência).

Prioridade do body gerado:
    1. ``example`` inline no requestBody          → sem LLM
    2. ``examples`` (mapa) no requestBody         → sem LLM
    3. ``example`` no componente ``$ref``         → sem LLM
    4. Fallback: geração via LLM
"""

from __future__ import annotations

import json
import re
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ...domain.ports.llm import ILlmClient

RATE_LIMIT_DELAY = 0.5
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


# ─── Utilitários OpenAPI (funções puras) ──────────────────────────────────


def resolve_ref(ref: str, root: dict) -> dict:
    if not ref.startswith("#/"):
        return {}
    node: Any = root
    for part in ref.lstrip("#/").split("/"):
        node = node.get(part, {})
    return deepcopy(node)


def resolve_schema(schema: dict, root: dict, depth: int = 0) -> dict:
    if depth > 8:
        return schema
    if "$ref" in schema:
        return resolve_schema(resolve_ref(schema["$ref"], root), root, depth + 1)
    schema = deepcopy(schema)
    if "properties" in schema:
        for key, val in schema["properties"].items():
            schema["properties"][key] = resolve_schema(val, root, depth + 1)
    if "items" in schema:
        schema["items"] = resolve_schema(schema["items"], root, depth + 1)
    for kw in ("allOf", "anyOf", "oneOf"):
        if kw in schema:
            schema[kw] = [resolve_schema(s, root, depth + 1) for s in schema[kw]]
    return schema


def find_example_in_ref(schema_raw: dict, root: dict) -> Optional[dict]:
    if "$ref" not in schema_raw:
        return None
    return resolve_ref(schema_raw["$ref"], root).get("example")


def get_request_body_info(operation: dict, root: dict) -> Tuple[Optional[dict], Any]:
    content = operation.get("requestBody", {}).get("content", {})
    ordered = sorted(content.items(), key=lambda kv: 0 if "application/json" in kv[0] else 1)
    for _, cinfo in ordered:
        schema_raw = cinfo.get("schema", {})
        resolved = resolve_schema(schema_raw, root)
        example = cinfo.get("example")
        if example is not None:
            return resolved, example
        examples_map = cinfo.get("examples", {})
        if examples_map:
            first = next(iter(examples_map.values()), None)
            if isinstance(first, dict):
                candidate = first.get("value", first)
                if candidate and not all(k in ("summary", "description") for k in candidate):
                    return resolved, candidate
        example = find_example_in_ref(schema_raw, root)
        if example is not None:
            return resolved, example
        return resolved, None
    return None, None


def get_path_params(operation: dict, path: str, root: dict) -> dict:
    result: Dict[str, Any] = {}
    for param in operation.get("parameters", []):
        if param.get("in") != "path":
            continue
        name = param["name"]
        schema = resolve_schema(param.get("schema", {}), root)
        if "enum" in schema:
            result[name] = schema["enum"][0]
        elif "example" in schema:
            result[name] = schema["example"]
        elif "example" in param:
            result[name] = param["example"]
        elif schema.get("type") == "integer":
            result[name] = 1
        elif schema.get("format") in ("uuid", "UUID"):
            result[name] = "00000000-0000-0000-0000-000000000001"
        else:
            result[name] = f"exemplo_{name}"
    for placeholder in re.findall(r"\{(\w+)\}", path):
        result.setdefault(placeholder, f"exemplo_{placeholder}")
    return result


def build_prompt(method: str, path: str, schema: dict, path_params: dict) -> str:
    parts = [
        "Você é um gerador de dados de teste para APIs REST.",
        "Gere um JSON de teste realista para a requisição abaixo.",
        "",
        f"Endpoint: {method.upper()} {path}",
    ]
    if path_params:
        parts += [
            "",
            "Parâmetros de path (já resolvidos — NÃO inclua no body):",
            json.dumps(path_params, ensure_ascii=False, indent=2),
        ]
    if schema:
        parts += ["", "Schema do requestBody (resolvido):", json.dumps(schema, ensure_ascii=False, indent=2)]
    parts += [
        "",
        "Regras:",
        "- Retorne APENAS o JSON do body, sem explicações, sem blocos markdown.",
        "- Use dados realistas em português brasileiro.",
        "- Respeite tipos, enums e campos required do schema.",
        "- Não inclua parâmetros de path, query ou headers no JSON.",
        "- Se não houver requestBody, retorne exatamente: {}",
    ]
    return "\n".join(parts)


def parse_llm_json(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def filter_fields_by_schema(data: Any, schema: Optional[dict]) -> Any:
    if schema is None:
        return data
    if schema.get("type") == "array" and "items" in schema:
        if isinstance(data, list):
            return [filter_fields_by_schema(item, schema["items"]) for item in data]
        return data
    if schema.get("type") == "object" and "properties" in schema and isinstance(data, dict):
        props = schema["properties"]
        return {key: filter_fields_by_schema(data[key], props[key]) for key in props if key in data}
    return data


def make_filename(method: str, path: str) -> str:
    sanitized = path.lstrip("/")
    sanitized = re.sub(r"\{[^}/]+\}", "X", sanitized)
    sanitized = re.sub(r"[/\\\s]+", "_", sanitized)
    sanitized = re.sub(r"[^a-zA-Z0-9_\-]", "", sanitized)
    return f"{method.upper()}_{sanitized}.json"


# ─── Adapter ───────────────────────────────────────────────────────────────


class ExampleDataGeneratorAdapter:
    """Gera dados de exemplo e os persiste em ``data_dir``."""

    def __init__(
        self,
        llm_client: ILlmClient,
        llm_model: str,
        data_dir: Path,
        rate_limit_delay: float = RATE_LIMIT_DELAY,
    ) -> None:
        self._llm = llm_client
        self._model = llm_model
        self._data_dir = data_dir
        self._delay = rate_limit_delay

    def generate(self, openapi: Dict[str, Any], only_with_body: bool = True) -> int:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        paths = openapi.get("paths", {})
        generated = 0

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                    continue

                schema, example = get_request_body_info(operation, openapi)
                has_body = bool(schema or example)
                if only_with_body and not has_body:
                    continue

                path_params = get_path_params(operation, path, openapi)

                if example is not None:
                    body = example if isinstance(example, dict) else {}
                else:
                    try:
                        raw = self._llm.generate(
                            build_prompt(method, path, schema or {}, path_params), self._model
                        )
                        body = filter_fields_by_schema(parse_llm_json(raw), schema)
                        time.sleep(self._delay)
                    except Exception as exc:  # noqa: BLE001 - registra e continua
                        print(f"    ❌ Erro LLM em {method.upper()} {path}: {exc}")
                        continue

                result: Dict[str, Any] = {}
                if path_params:
                    result["_path_params"] = path_params
                result.update(body)

                out_file = self._data_dir / make_filename(method, path)
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                generated += 1

        return generated
