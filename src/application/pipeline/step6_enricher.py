
'''
auto_enricher.py

Este script processa um arquivo OpenAPI/Swagger (JSON ou YAML) e gera o arquivo output/enriched_endpoints.json,
contendo uma lista enriquecida dos endpoints da API.

Principais funcionalidades:
- Extrai todos os endpoints e métodos HTTP do OpenAPI.
- Para cada endpoint, busca exemplos reais de requisição em output/tests/dados, se disponíveis.
- Preenche automaticamente o campo "roles" de cada endpoint, consultando as roles configuradas no arquivo Krakend
    (definido pela variável KRAKEND_CONF no .env). Faz substituição automática de variáveis como $ENDPOINT_PREFIX.
- Gera um relatório simples com o total de endpoints processados.

Com isso, o enriched_endpoints.json pode ser usado para geração de testes, documentação ou análise de segurança,
sempre refletindo a configuração real do gateway e exemplos reais de uso.
'''

import argparse
import json
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


class AutoEnricher:
    def __init__(self, input_file):
        self.input_file = Path(input_file)

    def enrich(self):
        data = self._load_input()

        enriched_endpoints = self._enrich_data(data)

        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = Path("src/application/pipeline/tests/enriched_endpoints.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(enriched_endpoints, f, indent=2, ensure_ascii=False)

        self._generate_report(enriched_endpoints, output_path)

        return enriched_endpoints

    def _load_input(self):
        if not self.input_file.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {self.input_file}")

        with open(self.input_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Detecta JSON ou YAML
        if self.input_file.suffix in [".yaml", ".yml"]:
            if not yaml:
                raise ImportError("PyYAML não instalado. Rode: pip install pyyaml")
            return yaml.safe_load(content)
        else:
            return json.loads(content)

    def _enrich_data(self, data):
        enriched = []

        paths = data.get("paths", {})

        VALID_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}
        exemplos_dir = Path("output/tests/dados")

        # Busca KRAKEND_CONF do .env
        import os
        krakend_conf = None
        endpoint_prefix = None
        env_path = Path(".env")
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("KRAKEND_CONF"):
                        krakend_conf = line.strip().split("=", 1)[-1]
                    if line.strip().startswith("ENDPOINT_PREFIX"):
                        endpoint_prefix = line.strip().split("=", 1)[-1]
        krakend_roles = {}
        if krakend_conf and Path(krakend_conf).exists():
            try:
                with open(krakend_conf, "r", encoding="utf-8") as f:
                    krakend_data = json.load(f)
                for ep in krakend_data.get("endpoints", []):
                    ep_path = ep.get("endpoint", "")
                    if endpoint_prefix:
                        ep_path = ep_path.replace("$ENDPOINT_PREFIX", endpoint_prefix)
                    ep_method = ep.get("method", "").upper()
                    # Busca roles no extra_config
                    roles = None
                    extra = ep.get("extra_config", {})
                    jose = extra.get("github.com/devopsfaith/krakend-jose/validator")
                    if jose and "roles" in jose:
                        roles = jose["roles"]
                    if roles:
                        krakend_roles[(ep_path, ep_method)] = roles
            except Exception as e:
                print(f"⚠️ Erro ao ler roles do Krakend: {e}")

        def make_example_filename(method, path):
            sanitized = path.lstrip("/")
            import re
            sanitized = re.sub(r"\{[^}/]+\}", "X", sanitized)
            sanitized = re.sub(r"[/\\\s]+", "_", sanitized)
            sanitized = re.sub(r"[^a-zA-Z0-9_\-]", "", sanitized)
            return f"{method.upper()}_{sanitized}.json"

        for path, methods in paths.items():
            if not isinstance(methods, dict):
                print(f"⚠️ Ignorando path inválido: {path}")
                continue

            for method, details in methods.items():
                if method.lower() not in VALID_METHODS:
                    continue
                if not isinstance(details, dict):
                    print(f"⚠️ Ignorando método inválido: {method} em {path}")
                    continue

                valid_request = None
                example_filename = make_example_filename(method, path)
                example_path = exemplos_dir / example_filename
                if example_path.exists():
                    try:
                        with open(example_path, "r", encoding="utf-8") as exf:
                            valid_request = json.load(exf)
                    except Exception as e:
                        print(f"⚠️ Erro ao ler exemplo {example_path}: {e}")

                # Busca roles do Krakend
                roles = []
                # Substitui variáveis de path do Krakend por {X} para bater com o OpenAPI
                def normalize_path(p):
                    import re
                    return re.sub(r"\{[^}/]+\}", "{X}", p)
                norm_path = normalize_path(path)
                # Tenta match exato, depois tenta ignorando variáveis
                found_roles = krakend_roles.get((path, method.upper()))
                if not found_roles:
                    # Tenta match por path normalizado
                    for (k_path, k_method), k_roles in krakend_roles.items():
                        if k_method == method.upper():
                            if normalize_path(k_path) == norm_path:
                                found_roles = k_roles
                                break
                if found_roles:
                    roles = found_roles

                endpoint = {
                    "path": path,
                    "method": method.upper(),
                    "summary": details.get("summary"),
                    "description": details.get("description"),
                    "business_context": {
                        "domain": "unknown"
                    },
                    "realistic_examples": {
                        "valid_request": valid_request,
                        "valid_response": None
                    },
                    "roles": roles
                }

                enriched.append(endpoint)

        return enriched

    def _generate_report(self, enriched_endpoints, output_path):
        print("\n📊 Relatório de Enriquecimento:")
        print(f"   Total endpoints enriquecidos: {len(enriched_endpoints)}")
        print(f"   Arquivo gerado: {output_path}")
        print("\n" + "="*72)
        print(f"   ⚠️  ATENÇÃO! REVISE {output_path} PARA CADA ENDPOINT")
        print("          Certifique-se de que 'roles' e 'realistic_examples' ")
        print("        estão corretos e completos para evitar erros nos testes.")
        print("="*72 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Gerador automático de enriched_endpoints.json"
    )
    parser.add_argument(
        "input_file",
        help="Arquivo OpenAPI/Swagger (JSON ou YAML)"
    )
    parser.add_argument(
        "--source",
        "-s",
        help="Caminho do código fonte da API (opcional, ignorado nesta versão)"
    )

    args = parser.parse_args()

    enricher = AutoEnricher(args.input_file)
    enricher.enrich()


if __name__ == "__main__":
    main()