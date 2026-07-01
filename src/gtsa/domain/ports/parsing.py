"""Port para parsers de código-fonte."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class ISourceParser(Protocol):
    """Extrai endpoints de API a partir do código-fonte de um arquivo."""

    def supports_file(self, file_path: str) -> bool: ...

    def extract_api_endpoints(
        self, code: str, file_path: str, source_root: Optional[str] = None
    ) -> List[Dict[str, Any]]: ...

    def get_ast_summary(self, code: str) -> Dict[str, Any]: ...


@runtime_checkable
class ISourceParserFactory(Protocol):
    """Cria o parser adequado para uma linguagem e detecta a linguagem do projeto."""

    def detect_language(self, project_path: str) -> Optional[str]: ...

    def create(self, language: str, debug: bool = False) -> ISourceParser: ...


@runtime_checkable
class ISourceScanner(Protocol):
    """Varre um projeto e persiste os endpoints extraídos em um diretório de scan."""

    def scan(
        self,
        project_path: str,
        language: Optional[str] = None,
        output_dir: Optional[str] = None,
        debug: bool = False,
    ) -> "ScanOutcome": ...


class ScanOutcome(Protocol):
    """Resultado de uma varredura: caminho do scan e endpoints achatados."""

    scan_dir: str
    endpoints: List[Dict[str, Any]]

