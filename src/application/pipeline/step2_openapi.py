#!/usr/bin/env python3
"""
step2_openapi.py
-------------------
Script para gerar um schema OpenAPI 3.0 automaticamente a partir de um arquivo all_endpoints.json (gerado pelo step1_scan.py).

Funcionalidades:
- Lê endpoints de um JSON e converte para o formato OpenAPI (openapi.json e openapi.yaml).
- Permite customizar título, versão e prefixo dos endpoints via argumentos de linha de comando.
- Gera também um relatório em Markdown com resumo dos endpoints.

Parâmetros de linha de comando:
    --env-file  Arquivo .env para carregar configurações (ex: .env.serproid)
    --title     Título da API (padrão: "API Gerada")
    --version   Versão da API (padrão: "1.0.0")
    --prefix    Prefixo externo dos endpoints (ex: /api/v1)
    --base-url  URL base da API (ex: https://hom.serproid.serpro.gov.br)
    --output-dir Diretório para saída (padrão: ../../../output)

Exemplo de uso:
    python3 step2_openapi.py --env-file .env.serproid --output-dir output-serproid
    python3 step2_openapi.py --title "Minha API" --version 2.0.0 --output-dir output-serproid
"""


import json
import re
import argparse
from pathlib import Path
from typing import List, Dict, Any
import os
from dotenv import load_dotenv


class OpenAPIGenerator:
    def __init__(self, endpoints: List[Dict], title: str, version: str, prefix: str = None, base_url: str = None):
        self.endpoints = endpoints
        self.title = title
        self.version = version
        self.prefix = prefix or os.getenv("ENDPOINT_PREFIX", "/api/v1")
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://localhost")
        self.schema = self._create_base_schema()

    def _create_base_schema(self) -> Dict:
        return {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": "Schema gerado automaticamente"
            },
            "servers": [
                {"url": self.base_url}
            ],
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT"
                    }
                }
            }
        }

    def _infer_type(self, t: str) -> str:
        t = t.lower()
        if "int" in t or "number" in t:
            return "number"
        if "bool" in t:
            return "boolean"
        if "array" in t or "list" in t:
            return "array"
        if "object" in t:
            return "object"
        return "string"

    def _extract_path_params(self, path: str):
        # Suporta tanto :param quanto {param}
        params = re.findall(r':(\w+)', path)
        params.extend(re.findall(r'\{(\w+)\}', path))
        return list(set(params))  # Remove duplicatas

    def _parameters(self, endpoint: Dict):
        params = []
        path_params = self._extract_path_params(endpoint["path"])

        for p in path_params:
            params.append({
                "name": p,
                "in": "path",
                "required": True,
                "schema": {"type": "string"}
            })

        # Adiciona parâmetros de query do endpoint
        for p in endpoint.get("parameters", []):
            param_name = p.get("name", "")
            if param_name and param_name not in path_params:
                params.append({
                    "name": param_name,
                    "in": "query",
                    "required": p.get("required", False),
                    "schema": {"type": self._infer_type(p.get("type", "string"))}
                })

        return params

    def _get_operation_id(self, endpoint: Dict) -> str:
        """Gera um operationId único baseado no método e path"""
        method = endpoint["method"].lower()
        handler = endpoint.get("name", "endpoint")
        # Remove caracteres especiais do path para criar um ID único
        path_clean = re.sub(r'[^a-zA-Z0-9]', '_', endpoint["path"])
        return f"{method}_{path_clean}_{handler}"

    def generate(self):
        for ep in self.endpoints:
            # Substitui :param por {param} para OpenAPI
            backend_path = re.sub(r':(\w+)', r'{\1}', ep["path"])
            
            # Remove qualquer prefixo /api ou /api/v1 do início
            backend_path = re.sub(r'^/api(/v\d+)?', '', backend_path)
            
            # Garante que backend_path começa com /
            if not backend_path.startswith("/"):
                backend_path = f"/{backend_path}"
            
            # Força prefixo /api/v1
            prefix = self.prefix
            external_path = prefix + backend_path
            
            # Normaliza barras duplas
            external_path = re.sub(r'//+', '/', external_path)
            
            method = ep["method"].lower()

            if external_path not in self.schema["paths"]:
                self.schema["paths"][external_path] = {}

            self.schema["paths"][external_path][method] = {
                "summary": ep.get("name", "endpoint"),
                "description": ep.get("business_purpose", ""),
                "operationId": self._get_operation_id(ep),
                "parameters": self._parameters(ep),
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object"
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Bad Request"
                    },
                    "401": {
                        "description": "Unauthorized"
                    },
                    "403": {
                        "description": "Forbidden"
                    },
                    "404": {
                        "description": "Not Found"
                    },
                    "500": {
                        "description": "Internal Server Error"
                    }
                }
            }

            # Adiciona security se auth_required for True
            if ep.get("auth_required", False):
                self.schema["paths"][external_path][method]["security"] = [
                    {"bearerAuth": []}
                ]

        return self.schema

    def _sanitize(self, obj):
        """Sanitiza objetos para JSON (converte sets para lists)"""
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: self._sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._sanitize(v) for v in obj]
        return obj

    def save(self, output_dir: Path, filename="openapi.json"):
        output_dir.mkdir(parents=True, exist_ok=True)

        json_path = output_dir / filename

        # Aplica sanitização antes de salvar
        clean_schema = self._sanitize(self.schema)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(clean_schema, f, indent=2, ensure_ascii=False)

        # Tenta salvar YAML se PyYAML estiver instalado
        try:
            import yaml
            yaml_path = output_dir / filename.replace(".json", ".yaml")
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(clean_schema, f, allow_unicode=True, sort_keys=False)
            print(f"✔ YAML também gerado em: {yaml_path}")
        except ImportError:
            pass

        return json_path


def load_input(path: Path) -> List[Dict]:
    """Carrega o arquivo de entrada"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_report(schema: Dict, reports_dir: Path) -> Path:
    """Gera um relatório Markdown do OpenAPI"""
    report_path = reports_dir / "openapi_report.md"

    total_paths = len(schema["paths"])
    total_ops = sum(len(v) for v in schema["paths"].values())
    
    # Conta métodos por tipo
    methods_count = {}
    for path, operations in schema["paths"].items():
        for method in operations.keys():
            methods_count[method] = methods_count.get(method, 0) + 1

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Relatório OpenAPI\n\n")
        f.write(f"## Resumo\n\n")
        f.write(f"- **Título:** {schema['info']['title']}\n")
        f.write(f"- **Versão:** {schema['info']['version']}\n")
        f.write(f"- **Total de paths:** {total_paths}\n")
        f.write(f"- **Total de operações:** {total_ops}\n")
        f.write(f"- **Servidor:** {schema['servers'][0]['url']}\n\n")
        
        f.write(f"## Métodos por Tipo\n\n")
        for method, count in sorted(methods_count.items()):
            f.write(f"- **{method.upper()}:** {count}\n")
        
        f.write(f"\n## Lista de Endpoints\n\n")
        f.write("| Método | Path | Summary |\n")
        f.write("|--------|------|---------|\n")
        for path, operations in sorted(schema["paths"].items()):
            for method, details in operations.items():
                summary = details.get("summary", "")
                f.write(f"| {method.upper()} | `{path}` | {summary} |\n")

    return report_path


def find_latest_input() -> Path:
    """Encontra o arquivo all_endpoints.json mais recente"""
    scan_root = Path("src/application/pipeline/tests")
    
    if not scan_root.exists():
        print(f"❌ Diretório não encontrado: {scan_root}")
        return None
    
    scan_dirs = sorted([d for d in scan_root.glob("scan_*") if d.is_dir()], reverse=True)
    
    for d in scan_dirs:
        candidate = d / "all_endpoints.json"
        if candidate.exists():
            return candidate
    
    return None


def load_env_file(env_file: str) -> None:
    """Carrega um arquivo .env específico"""
    if env_file:
        env_path = Path(env_file)
        if env_path.exists():
            print(f"📄 Carregando arquivo .env: {env_path}")
            load_dotenv(env_path, override=True)
        else:
            print(f"⚠️  Arquivo .env não encontrado: {env_path}")
            print("   Usando variáveis de ambiente existentes ou padrões.")


def main():
    parser = argparse.ArgumentParser(
        description="Gerador OpenAPI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXEMPLOS:
  # Usando um arquivo .env específico
  python3 step2_openapi.py --env-file .env.serproid --output-dir output-serproid
  
  # Sobrescrevendo configurações manualmente
  python3 step2_openapi.py --base-url "https://hom.serproid.serpro.gov.br" --prefix "/oauth/v1/oauth"
"""
    )
    parser.add_argument("--env-file", help="Arquivo .env para carregar configurações (ex: .env.serproid)")
    parser.add_argument("--title", default=None, help="Título da API (padrão: valor do .env ou 'API Gerada')")
    parser.add_argument("--version", default=None, help="Versão da API (padrão: valor do .env ou '1.0.0')")
    parser.add_argument("--prefix", default=None, help="Prefixo externo dos endpoints (padrão: valor do .env ou '/api/v1')")
    parser.add_argument("--base-url", default=None, help="URL base da API (padrão: valor do .env ou 'http://localhost')")
    parser.add_argument("--output-dir", default=None, help='Diretório para saída (padrão: ../../../output)')
    args = parser.parse_args()

    # ─── CARREGA O .ENV ──────────────────────────────────────────────────
    load_env_file(args.env_file)

    # ─── DEFINE CONFIGURAÇÕES (prioridade: args > .env > padrão) ──────
    title = args.title or os.getenv("API_TITLE", "API Gerada")
    version = args.version or os.getenv("API_VERSION", "1.0.0")
    prefix = args.prefix or os.getenv("ENDPOINT_PREFIX", "/api/v1")
    base_url = args.base_url or os.getenv("API_BASE_URL", "http://localhost")

    print("=" * 60)
    print("📋 Configurações carregadas:")
    print(f"   - API_BASE_URL: {base_url}")
    print(f"   - ENDPOINT_PREFIX: {prefix}")
    print(f"   - Título: {title}")
    print(f"   - Versão: {version}")
    print("=" * 60)

    # Busca automática do arquivo all_endpoints.json mais recente
    input_path = find_latest_input()
    if not input_path:
        print("❌ Nenhum arquivo all_endpoints.json encontrado em src/application/pipeline/tests/scan_*/")
        print("   Execute o step1_scan.py primeiro para gerar os endpoints.")
        exit(1)

    print(f"ℹ️ Usando arquivo de entrada: {input_path}")
    endpoints = load_input(input_path)

    # Define o diretório de saída
    if args.output_dir:
        output_dir = Path(args.output_dir)
        # Se for relativo, resolve a partir da raiz do projeto
        if not output_dir.is_absolute():
            project_root = Path(__file__).parent.parent.parent.parent
            output_dir = project_root / args.output_dir
    else:
        # Default: ../../../output
        output_dir = Path(__file__).parent.parent.parent / "output"
    
    output_dir = output_dir.resolve()
    print(f"📁 Diretório de saída: {output_dir}")

    # Gera o OpenAPI
    generator = OpenAPIGenerator(
        endpoints, 
        title=title, 
        version=version, 
        prefix=prefix,
        base_url=base_url
    )
    
    schema = generator.generate()
    json_path = generator.save(output_dir)
    report_path = generate_report(schema, output_dir)

    print(f"\n✅ OpenAPI gerado com sucesso!")
    print(f"   📄 JSON: {json_path}")
    print(f"   📄 Relatório: {report_path}")
    
    # Mostra um resumo das configurações usadas no OpenAPI
    print(f"\n📋 Resumo do OpenAPI gerado:")
    print(f"   - Servidor: {schema['servers'][0]['url']}")
    print(f"   - Prefixo dos paths: {prefix}")
    print(f"   - Total de paths: {len(schema['paths'])}")
    print(f"   - Total de operações: {sum(len(v) for v in schema['paths'].values())}")


if __name__ == "__main__":
    main()