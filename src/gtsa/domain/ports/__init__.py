"""Ports do domínio: interfaces (Protocols) que a camada de aplicação consome.

Os adapters concretos vivem em ``gtsa.infrastructure`` e são ligados aos
casos de uso pelo composition root (``gtsa.bootstrap``).
"""

from .analysis import IPiiDetector, IVulnerabilityAnalyzer
from .auth import IAuthProvider
from .examples import IExampleDataGenerator
from .http import IHttpClient
from .llm import ILlmClient
from .openapi import IOpenApiGenerator
from .parsing import ISourceParser, ISourceParserFactory
from .reporting import IReportBuilder
from .storage import IArtifactStore, IEndpointRepository
from .testing import ITestRunner

__all__ = [
    "IPiiDetector",
    "IVulnerabilityAnalyzer",
    "IAuthProvider",
    "IExampleDataGenerator",
    "IHttpClient",
    "ILlmClient",
    "IOpenApiGenerator",
    "ISourceParser",
    "ISourceParserFactory",
    "IReportBuilder",
    "IArtifactStore",
    "IEndpointRepository",
    "ITestRunner",
]
