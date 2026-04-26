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
    --title     Título da API (padrão: "API Gerada")
    --version   Versão da API (padrão: "1.0.0")
    --prefix    Prefixo externo dos endpoints (ex: /api/v1)

Exemplo de uso:
        python3 step2_openapi.py --title "Minha API" --version 2.0.0

Saídas:
- output/openapi.json   (schema OpenAPI gerado)
- output/openapi.yaml   (opcional, se PyYAML instalado)
- output/report.md      (relatório resumido dos endpoints)
"""


import json
import re
import argparse
from pathlib import Path
from typing import List, Dict, Any
import os
from dotenv import load_dotenv


class OpenAPIGenerator:
    def __init__(self, endpoints: List[Dict], title: str, version: str, prefix: str = None):
        self.endpoints = endpoints
        self.title = title
        self.version = version
        self.schema = self._create_base_schema()
        # Prefixo externo (ex: /api/v1) para os endpoints
        self.prefix = prefix or os.getenv("ENDPOINT_PREFIX", "/api/v1")

    def _create_base_schema(self) -> Dict:
        # Prioridade: variável de ambiente API_BASE_URL > .env > default
        api_base_url = os.getenv("API_BASE_URL", "http://localhost")
        return {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": "Schema gerado automaticamente"
            },
            "servers": [
                {"url": api_base_url}
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
        return re.findall(r':(\w+)', path)

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

        for p in endpoint.get("parameters", []):
            if p["name"] not in path_params:
                params.append({
                    "name": p["name"],
                    "in": "query",
                    "required": False,
                    "schema": {"type": self._infer_type(p.get("type", "string"))}
                })

        return params

    def generate(self):
        for ep in self.endpoints:
            # Substitui :param por {param} para OpenAPI
            backend_path = re.sub(r':(\w+)', r'{\1}', ep["path"])
            # Remove qualquer prefixo /api ou /api/v1 do início
            backend_path = re.sub(r'^/api(/v\d+)?', '', backend_path)
            # Garante que backend_path começa com /
            backend_path = backend_path if backend_path.startswith("/") else f"/{backend_path}"
            # Força prefixo /api/v1
            prefix = "/api/v1"
            external_path = prefix + backend_path
            # Normaliza barras duplas
            external_path = re.sub(r'//+', '/', external_path)
            method = ep["method"].lower()

            if external_path not in self.schema["paths"]:
                self.schema["paths"][external_path] = {}

            self.schema["paths"][external_path][method] = {
                "summary": ep.get("name", "endpoint"),
                "description": ep.get("business_purpose", ""),
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
                    }
                }
            }

        return self.schema

    # 🔥 FUNÇÃO NOVA (corrige erro de set)
    def _sanitize(self, obj):
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

        # ✅ aplica sanitização antes de salvar
        clean_schema = self._sanitize(self.schema)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(clean_schema, f, indent=2, ensure_ascii=False)

        # opcional YAML
        try:
            import yaml
            yaml_path = output_dir / filename.replace(".json", ".yaml")
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(clean_schema, f, allow_unicode=True, sort_keys=False)
        except ImportError:
            pass

        return json_path


def load_input(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_report(schema: Dict, output_dir: Path):
    report_path = output_dir / "openapi.json-report.md"

    total_paths = len(schema["paths"])
    total_ops = sum(len(v) for v in schema["paths"].values())

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Relatório OpenAPI\n\n")
        f.write(f"- Paths: {total_paths}\n")
        f.write(f"- Operações: {total_ops}\n")

    return report_path



def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Gerador OpenAPI")
    parser.add_argument("--title", default="API Gerada")
    parser.add_argument("--version", default="1.0.0")
    parser.add_argument("--prefix", default=None, help="Prefixo externo dos endpoints (ex: /api/v1)")

    args = parser.parse_args()
    output_dir = Path("output")

    # Busca automática do arquivo all_endpoints.json mais recente
    ast_dir = Path("output")
    scan_dirs = sorted([d for d in ast_dir.glob("scan_*") if d.is_dir()], reverse=True)
    input_path = None
    for d in scan_dirs:
        candidate = d / "all_endpoints.json"
        if candidate.exists():
            input_path = candidate
            break
    if not input_path:
        print("❌ Nenhum arquivo all_endpoints.json encontrado em output/ast/scan_*/")
        exit(1)

    print(f"ℹ️ Usando arquivo de entrada: {input_path}")
    endpoints = load_input(input_path)

    # Prioridade: argumento CLI > .env > default
    generator = OpenAPIGenerator(endpoints, args.title, args.version, prefix=args.prefix)
    schema = generator.generate()
    json_path = generator.save(output_dir)
    report_path = generate_report(schema, output_dir)

    print(f"✔ OpenAPI gerado em: {json_path}")
    print(f"✔ Relatório gerado em: {report_path}")


if __name__ == "__main__":
    main()