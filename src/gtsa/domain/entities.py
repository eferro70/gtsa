"""Entidades de domínio do GTSA.

As entidades representam os conceitos centrais que fluem pela pipeline. Para
manter compatibilidade com os artefatos JSON já produzidos pela pipeline,
cada entidade expõe ``from_dict``/``to_dict``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .value_objects import RiskLevel


@dataclass
class ApiEndpoint:
    """Um endpoint de API extraído do código-fonte ou da especificação OpenAPI."""

    method: str
    path: str
    handler: str = ""
    file: str = ""
    line_number: Optional[int] = None
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    context: Optional[str] = None
    auth_required: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApiEndpoint":
        known = {
            "method", "path", "handler", "file", "line_number",
            "parameters", "context", "auth_required",
        }
        return cls(
            method=str(data.get("method", "")),
            path=str(data.get("path", "")),
            handler=str(data.get("handler") or data.get("name") or ""),
            file=str(data.get("file", "")),
            line_number=data.get("line_number"),
            parameters=list(data.get("parameters", []) or []),
            context=data.get("context"),
            auth_required=bool(data.get("auth_required", False)),
            extra={k: v for k, v in data.items() if k not in known},
        )

    def to_dict(self) -> Dict[str, Any]:
        base: Dict[str, Any] = {
            "method": self.method,
            "path": self.path,
            "handler": self.handler,
            "file": self.file,
            "line_number": self.line_number,
            "parameters": self.parameters,
            "context": self.context,
            "auth_required": self.auth_required,
        }
        base.update(self.extra)
        return base


@dataclass
class SecurityFinding:
    """Achado de segurança associado a um endpoint."""

    endpoint_method: str
    endpoint_path: str
    vulnerability_id: str
    name: str
    risk_level: RiskLevel = RiskLevel.NONE
    owasp_id: str = ""
    cwe_id: str = ""
    description: str = ""
    remediation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.endpoint_method,
            "path": self.endpoint_path,
            "vulnerability_id": self.vulnerability_id,
            "name": self.name,
            "risk_level": self.risk_level.value,
            "owasp_id": self.owasp_id,
            "cwe_id": self.cwe_id,
            "description": self.description,
            "remediation": self.remediation,
        }


@dataclass
class ExampleData:
    """Dados de exemplo (payload/params) para um endpoint."""

    method: str
    path: str
    body: Optional[Dict[str, Any]] = None
    path_params: Dict[str, Any] = field(default_factory=dict)
    query_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Resultado consolidado de uma operação testada pelo Schemathesis."""

    endpoint: str
    passed: int = 0
    failed: int = 0
    errored: int = 0
    skipped: int = 0
    failures: List[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.errored + self.skipped
