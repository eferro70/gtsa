"""``Settings``: configuração centralizada carregada uma única vez do ambiente.

Substitui a leitura ad-hoc de ``os.getenv`` espalhada pelos steps. O
carregamento de arquivos ``.env`` segue a mesma estratégia de prioridade do
antigo ``utils/env_loader.py``:

1. Arquivos ``.env`` genéricos (fallback, sem override).
2. Arquivo específico do usuário (``--env-file``), com override.
3. ``.env.local`` (override final).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


def _project_root() -> Path:
    # src/gtsa/infrastructure/config/settings.py -> raiz do projeto
    return Path(__file__).resolve().parents[4]


def load_dotenv_files(env_file: Optional[str] = None, verbose: bool = False) -> None:
    """Carrega arquivos .env na ordem de prioridade do projeto."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        if verbose:
            print("⚠️  python-dotenv não instalado; variáveis do .env não serão carregadas.")
        return

    root = _project_root()

    # 1. Fallbacks genéricos (sem override)
    for candidate in (root / ".env", Path(".env")):
        if candidate.exists():
            load_dotenv(candidate, override=False)
            if verbose:
                print(f"📄 Fallback .env: {candidate}")

    # 2. Arquivo específico do usuário (override)
    if env_file:
        env_path = Path(env_file)
        if env_path.exists():
            load_dotenv(env_path, override=True)
            if verbose:
                print(f"✅ Carregado (override): {env_path}")
        elif verbose:
            print(f"⚠️  Arquivo .env especificado não encontrado: {env_file}")

    # 3. .env.local (override final)
    local_env = root / ".env.local"
    if local_env.exists():
        load_dotenv(local_env, override=True)
        if verbose:
            print(f"✅ Sobrescrito por: {local_env}")


def load_environment(env_file: Optional[str] = None, verbose: bool = False) -> None:
    """Alias de compatibilidade para ``load_dotenv_files``."""
    load_dotenv_files(env_file, verbose=verbose)


def add_env_arg(parser) -> None:
    """Adiciona o argumento ``--env-file`` a um ``argparse.ArgumentParser``."""
    parser.add_argument(
        "--env-file", help="Caminho para o arquivo .env (ex: .env.serproid)", default=None
    )


def get_env_file_from_args(args) -> Optional[str]:
    return getattr(args, "env_file", None)


def _split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass
class Settings:
    """Configuração imutável da pipeline, resolvida a partir do ambiente."""

    # Identidade / caminhos
    api_name: str = ""
    project_root: Path = field(default_factory=_project_root)
    output_dir: Path = field(default_factory=lambda: _project_root() / "output")
    runtime_dir: Path = field(default_factory=lambda: _project_root() / "runtime")
    config_dir: Path = field(default_factory=lambda: _project_root() / "config")
    env_file: Optional[str] = None

    # API alvo
    api_base_url: str = "http://localhost"
    endpoint_prefix: str = "/api/v1"
    api_title: str = "API Gerada"
    api_version: str = "1.0.0"
    openapi_json: Optional[str] = None

    # LLM
    llm_backend: str = "ollama"
    llm_model: str = "gemma"
    llm_base_url: Optional[str] = None

    # Autenticação
    auth_type: str = ""
    auth_profile: str = ""
    auth_cookie_name: str = ""
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer "

    # Testes
    only_high_risk: bool = False
    skip_endpoints: List[str] = field(default_factory=list)
    skip_methods: List[str] = field(default_factory=list)
    max_examples: int = 10
    verbose: bool = False
    debug: bool = False

    @property
    def data_dir(self) -> Path:
        """Diretório dos dados de exemplo (runtime)."""
        return self.runtime_dir / "dados"

    @property
    def scans_dir(self) -> Path:
        """Diretório dos scans (runtime)."""
        return self.runtime_dir / "scans"

    def env(self, name: str, default: str = "") -> str:
        """Acesso pontual a variáveis de ambiente ainda não mapeadas."""
        return os.getenv(name, default)


def load_settings(
    api_name: str = "",
    env_file: Optional[str] = None,
    output_dir: Optional[str] = None,
    verbose: bool = False,
    debug: bool = False,
) -> Settings:
    """Carrega os arquivos .env e monta o objeto ``Settings``."""
    load_dotenv_files(env_file, verbose=verbose)

    root = _project_root()
    resolved_output = (
        Path(output_dir) if output_dir else root / f"output-{api_name}" if api_name else root / "output"
    )
    if not resolved_output.is_absolute():
        resolved_output = root / resolved_output

    return Settings(
        api_name=api_name or os.getenv("API_NAME", ""),
        project_root=root,
        output_dir=resolved_output.resolve(),
        runtime_dir=root / "runtime",
        config_dir=root / "config",
        env_file=env_file,
        api_base_url=os.getenv("API_BASE_URL", "http://localhost"),
        endpoint_prefix=os.getenv("ENDPOINT_PREFIX", "/api/v1"),
        api_title=os.getenv("API_TITLE", "API Gerada"),
        api_version=os.getenv("API_VERSION", "1.0.0"),
        openapi_json=os.getenv("OPENAPI_JSON"),
        llm_backend=os.getenv("LLM_BACKEND", "ollama").lower(),
        llm_model=os.getenv("LLM_MODEL", "gemma"),
        llm_base_url=os.getenv("LLM_BASE_URL"),
        auth_type=os.getenv("AUTH_TYPE", "").strip().lower(),
        auth_profile=os.getenv("AUTH_PROFILE", "").strip().upper(),
        auth_cookie_name=os.getenv("AUTH_COOKIE_NAME", "").strip(),
        auth_header=os.getenv("AUTH_HEADER", "Authorization"),
        auth_prefix=os.getenv("AUTH_PREFIX", "Bearer "),
        only_high_risk=os.getenv("ONLY_HIGH_RISK", "false").lower() == "true",
        skip_endpoints=_split_csv(os.getenv("SKIP_ENDPOINTS", "")),
        skip_methods=_split_csv(os.getenv("SKIP_METHODS", "TRACE,OPTIONS,HEAD")),
        max_examples=int(os.getenv("MAX_EXAMPLES", "10") or "10"),
        verbose=verbose or os.getenv("VERBOSE", "false").lower() == "true",
        debug=debug or os.getenv("PYTHON_DEBUG", "false").lower() == "true",
    )
