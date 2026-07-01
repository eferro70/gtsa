"""Hierarquia de erros de domínio do GTSA."""

from __future__ import annotations


class GtsaError(Exception):
    """Erro base de todo o domínio GTSA."""


class ConfigurationError(GtsaError):
    """Configuração ausente ou inválida (ex.: variável de ambiente faltando)."""


class ParserError(GtsaError):
    """Falha ao extrair endpoints do código-fonte."""


class UnsupportedLanguageError(ParserError):
    """Linguagem do projeto não suportada por nenhum parser disponível."""


class OpenApiGenerationError(GtsaError):
    """Falha ao gerar a especificação OpenAPI."""


class ExampleGenerationError(GtsaError):
    """Falha ao gerar dados de exemplo para os endpoints."""


class AnalysisError(GtsaError):
    """Falha durante a análise de vulnerabilidades e enriquecimento."""


class AuthenticationError(GtsaError):
    """Falha ao montar ou obter credenciais de autenticação."""


class TestExecutionError(GtsaError):
    """Falha ao executar a suíte de testes (Schemathesis)."""


class ReportGenerationError(GtsaError):
    """Falha ao gerar o relatório final."""
