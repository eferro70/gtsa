"""Gerador de especificação OpenAPI 3.0 a partir de endpoints extraídos.

Implementa ``IOpenApiGenerator``. Consolida a lógica que vivia dentro do
``step2_openapi.py``.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


class OpenApiGeneratorAdapter:
    """Converte uma lista de endpoints em um documento OpenAPI 3.0."""

    def __init__(
        self,
        title: str = "API Gerada",
        version: str = "1.0.0",
        prefix: str = "/api/v1",
        base_url: str = "http://localhost",
    ) -> None:
        self.title = title
        self.version = version
        self.prefix = prefix
        self.base_url = base_url

    # -- API pública -------------------------------------------------------

    def generate(self, endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
        schema = self._base_schema()
        for ep in endpoints:
            external_path = self._external_path(ep["path"])
            method = ep["method"].lower()
            schema["paths"].setdefault(external_path, {})
            schema["paths"][external_path][method] = self._operation(ep)
            if ep.get("auth_required", False):
                schema["paths"][external_path][method]["security"] = [{"bearerAuth": []}]
        return self._sanitize(schema)

    # -- Internos ----------------------------------------------------------

    def _base_schema(self) -> Dict[str, Any]:
        return {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": "Schema gerado automaticamente",
            },
            "servers": [{"url": self.base_url}],
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
                },
            },
        }

    def _external_path(self, raw_path: str) -> str:
        backend_path = re.sub(r":(\w+)", r"{\1}", raw_path)
        backend_path = re.sub(r"^/api(/v\d+)?", "", backend_path)
        if not backend_path.startswith("/"):
            backend_path = f"/{backend_path}"
        external = self.prefix + backend_path
        return re.sub(r"//+", "/", external)

    def _operation(self, endpoint: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "summary": endpoint.get("handler") or endpoint.get("name", "endpoint"),
            "description": endpoint.get("business_purpose", ""),
            "operationId": self._operation_id(endpoint),
            "parameters": self._parameters(endpoint),
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {"application/json": {"schema": {"type": "object"}}},
                },
                "400": {"description": "Bad Request"},
                "401": {"description": "Unauthorized"},
                "403": {"description": "Forbidden"},
                "404": {"description": "Not Found"},
                "500": {"description": "Internal Server Error"},
            },
        }

    @staticmethod
    def _infer_type(t: str) -> str:
        t = (t or "").lower()
        if "int" in t or "number" in t:
            return "number"
        if "bool" in t:
            return "boolean"
        if "array" in t or "list" in t:
            return "array"
        if "object" in t:
            return "object"
        return "string"

    @staticmethod
    def _extract_path_params(path: str) -> List[str]:
        params = re.findall(r":(\w+)", path)
        params.extend(re.findall(r"\{(\w+)\}", path))
        return list(set(params))

    def _parameters(self, endpoint: Dict[str, Any]) -> List[Dict[str, Any]]:
        params: List[Dict[str, Any]] = []
        path_params = self._extract_path_params(endpoint["path"])
        for name in path_params:
            params.append(
                {"name": name, "in": "path", "required": True, "schema": {"type": "string"}}
            )
        for p in endpoint.get("parameters", []) or []:
            param_name = p.get("name", "")
            if param_name and param_name not in path_params:
                params.append(
                    {
                        "name": param_name,
                        "in": "query",
                        "required": p.get("required", False),
                        "schema": {"type": self._infer_type(p.get("type", "string"))},
                    }
                )
        return params

    @staticmethod
    def _operation_id(endpoint: Dict[str, Any]) -> str:
        method = endpoint["method"].lower()
        handler = endpoint.get("handler") or endpoint.get("name", "endpoint")
        path_clean = re.sub(r"[^a-zA-Z0-9]", "_", endpoint["path"])
        return f"{method}_{path_clean}_{handler}"

    def _sanitize(self, obj: Any) -> Any:
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, dict):
            return {k: self._sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._sanitize(v) for v in obj]
        return obj
