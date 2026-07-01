"""Value objects do domínio GTSA."""

from __future__ import annotations

from enum import Enum


class HttpMethod(str, Enum):
    """Métodos HTTP suportados na análise de endpoints."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    TRACE = "TRACE"
    REQUEST = "REQUEST"

    @classmethod
    def parse(cls, value: str) -> "HttpMethod":
        try:
            return cls(value.strip().upper())
        except ValueError:
            return cls.REQUEST


class RiskLevel(str, Enum):
    """Nível de risco associado a um endpoint ou achado de segurança."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def is_high_or_above(self) -> bool:
        return self in (RiskLevel.HIGH, RiskLevel.CRITICAL)


class Role(str, Enum):
    """Perfis de autenticação reconhecidos pela pipeline."""

    ADMINISTRADOR = "ADMINISTRADOR"
    GESTOR = "GESTOR"
    REQUISITANTE = "REQUISITANTE"
    INTERESSADO = "INTERESSADO"
    PAV = "PAV"
    TESTE = "TESTE"
