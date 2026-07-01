"""Composition root (raiz de composição) da aplicação GTSA.

Responsável por instanciar os adapters de infraestrutura, injetá-los nos casos
de uso da aplicação e devolver um contêiner pronto para uso pelas interfaces
(CLI). É o único lugar onde a camada de interface conhece a infraestrutura,
preservando a regra de dependência da Clean Architecture.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .application.use_cases import (
    AnalyzeAndEnrichUseCase,
    BuildReportUseCase,
    GenerateExampleDataUseCase,
    GenerateOpenApiUseCase,
    RunSchemathesisUseCase,
    ScanSourceUseCase,
)
from .infrastructure.analysis import VulnerabilityAnalyzerAdapter
from .infrastructure.auth.auth_provider import AuthProvider
from .infrastructure.config.settings import Settings, load_settings
from .infrastructure.examples.generator import ExampleDataGeneratorAdapter
from .infrastructure.http.requests_client import RequestsHttpClient
from .infrastructure.llm.clients import create_llm_client
from .infrastructure.openapi.generator import OpenApiGeneratorAdapter
from .infrastructure.persistence.filesystem_store import FilesystemArtifactStore
from .infrastructure.reporting import MarkdownReportBuilderAdapter
from .infrastructure.scanning import SourceScannerAdapter
from .infrastructure.testing import SchemathesisRunnerAdapter


@dataclass
class Container:
    """Agrega configuração e casos de uso prontos para execução."""

    settings: Settings
    scan_source: ScanSourceUseCase
    generate_openapi: GenerateOpenApiUseCase
    generate_example_data: GenerateExampleDataUseCase
    analyze_and_enrich: AnalyzeAndEnrichUseCase
    run_schemathesis: RunSchemathesisUseCase
    build_report: BuildReportUseCase
    auth_provider: AuthProvider


def build_container(
    api_name: str = "",
    env_file: Optional[str] = None,
    output_dir: Optional[str] = None,
    verbose: bool = False,
    debug: bool = False,
    use_llm: bool = False,
) -> Container:
    """Constrói e conecta todas as dependências da pipeline."""
    settings = load_settings(
        api_name=api_name,
        env_file=env_file,
        output_dir=output_dir,
        verbose=verbose,
        debug=debug,
    )

    http_client = RequestsHttpClient()
    auth_provider = AuthProvider(http_client)
    llm_client = create_llm_client(settings.llm_backend, http_client, settings.llm_base_url)

    store = FilesystemArtifactStore(settings)

    scanner = SourceScannerAdapter(settings)
    openapi_generator = OpenApiGeneratorAdapter(
        title=settings.api_title,
        version=settings.api_version,
        prefix=settings.endpoint_prefix,
        base_url=settings.api_base_url,
    )
    example_generator = ExampleDataGeneratorAdapter(
        llm_client=llm_client,
        llm_model=settings.llm_model,
        data_dir=settings.data_dir,
    )
    analyzer = VulnerabilityAnalyzerAdapter(
        settings=settings,
        use_llm=use_llm,
        backend=settings.llm_backend,
        model=settings.llm_model,
        llm_url=settings.llm_base_url,
    )
    test_runner = SchemathesisRunnerAdapter(settings)
    report_builder = MarkdownReportBuilderAdapter(settings)

    return Container(
        settings=settings,
        scan_source=ScanSourceUseCase(scanner),
        generate_openapi=GenerateOpenApiUseCase(openapi_generator, store),
        generate_example_data=GenerateExampleDataUseCase(example_generator),
        analyze_and_enrich=AnalyzeAndEnrichUseCase(analyzer),
        run_schemathesis=RunSchemathesisUseCase(test_runner),
        build_report=BuildReportUseCase(report_builder),
        auth_provider=auth_provider,
    )
