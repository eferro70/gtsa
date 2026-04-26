#!/usr/bin/env python3
"""
gerar_dados_exemplo.py
Gera output/tests/dados/{METHOD}_{endpoint}.json para cada endpoint do openapi.json.

Prioridade para o body gerado:
    1. `example` inline no requestBody                → usa diretamente, SEM LLM
    2. `examples` (mapa) no requestBody              → pega o primeiro valor, SEM LLM
    3. `example` no componente $ref do schema        → usa diretamente, SEM LLM
    4. Fallback: gera via LLM (gatiator ou ollama)

Parâmetros de path são salvos em `_path_params` no JSON gerado.

Uso:
    python gerar_dados_exemplo.py <openapi.json>
    python gerar_dados_exemplo.py <openapi.json> --llm-backend ollama --llm-model llama3
    python gerar_dados_exemplo.py <openapi.json> --llm-backend gatiator --llm-model phi
    python gerar_dados_exemplo.py <openapi.json> --only-with-body
    python gerar_dados_exemplo.py <openapi.json> --no-overwrite
"""

import json
import os
import re
import sys
import time
import argparse
from pathlib import Path
from copy import deepcopy

# Carrega variáveis do .env automaticamente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv não instalado. Variáveis do .env não serão carregadas automaticamente.")

# ─── Configuração padrão ──────────────────────────────────────────────────────

DEFAULT_MODEL    = "codellama:7b"
RATE_LIMIT_DELAY = 0.5   # segundos entre chamadas ao LLM (rate limit)

# URLs fixas por backend — sobrepõe pelo argumento --llm-url se necessário
BACKEND_URLS = {
    "gatiator": "http://localhost:1313/v1/chat/completions",
    "ollama":   "http://localhost:11434/api/generate",
}

# Backend lido do .env; fallback para "ollama" se não definido
DEFAULT_BACKEND = os.getenv("LLM_BACKEND", "ollama").lower()
if DEFAULT_BACKEND not in BACKEND_URLS:
    print(f"⚠️  LLM_BACKEND='{DEFAULT_BACKEND}' inválido. Use 'gatiator' ou 'ollama'. Usando 'ollama'.")
    DEFAULT_BACKEND = "ollama"
DEFAULT_LLM_URL = BACKEND_URLS[DEFAULT_BACKEND]

# ─── Utilitários OpenAPI ──────────────────────────────────────────────────────

def load_openapi(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_ref(ref: str, root: dict) -> dict:
    """Resolve $ref local como '#/components/schemas/Foo' navegando no dict."""
    if not ref.startswith("#/"):
        return {}
    parts = ref.lstrip("#/").split("/")
    node = root
    for part in parts:
        node = node.get(part, {})
    return deepcopy(node)


def resolve_schema(schema: dict, root: dict, depth: int = 0) -> dict:
    """
    Expande $ref recursivamente.
    Limita profundidade para evitar loops em schemas circulares.
    """
    if depth > 8:
        return schema

    if "$ref" in schema:
        resolved = resolve_ref(schema["$ref"], root)
        return resolve_schema(resolved, root, depth + 1)

    schema = deepcopy(schema)

    if "properties" in schema:
        for key, val in schema["properties"].items():
            schema["properties"][key] = resolve_schema(val, root, depth + 1)

    if "items" in schema:
        schema["items"] = resolve_schema(schema["items"], root, depth + 1)

    for kw in ("allOf", "anyOf", "oneOf"):
        if kw in schema:
            schema[kw] = [resolve_schema(s, root, depth + 1) for s in schema[kw]]

    return schema


def find_example_in_ref(schema_raw: dict, root: dict) -> dict | None:
    """
    Se o schema for um $ref, verifica se o componente referenciado
    tem um campo `example` no topo (ex: components/schemas/Foo.example).
    """
    if "$ref" not in schema_raw:
        return None
    ref_target = resolve_ref(schema_raw["$ref"], root)
    return ref_target.get("example")  # None se não houver


def get_request_body_info(operation: dict, root: dict) -> tuple:
    """
    Retorna (schema_resolvido, example_or_None).

    Ordem de busca do example:
      1. requestBody.content.*.example        (inline direto)
      2. requestBody.content.*.examples       (mapa OpenAPI 3 → primeiro valor)
      3. example no $ref do schema            (no componente referenciado)
    """
    rb      = operation.get("requestBody", {})
    content = rb.get("content", {})

    # Prefere application/json, aceita qualquer outro com schema
    ordered = sorted(
        content.items(),
        key=lambda kv: 0 if "application/json" in kv[0] else 1
    )

    for _, cinfo in ordered:
        schema_raw = cinfo.get("schema", {})
        resolved   = resolve_schema(schema_raw, root)

        # 1. example inline
        example = cinfo.get("example")
        if example is not None:
            return resolved, example

        # 2. examples map (OpenAPI 3): {name: {summary, value}} ou {name: <obj>}
        examples_map = cinfo.get("examples", {})
        if examples_map:
            first = next(iter(examples_map.values()), None)
            if isinstance(first, dict):
                candidate = first.get("value", first)
                # evita retornar metadados (summary/description sem value)
                if candidate and not all(k in ("summary", "description") for k in candidate):
                    return resolved, candidate

        # 3. example no $ref
        example = find_example_in_ref(schema_raw, root)
        if example is not None:
            return resolved, example

        return resolved, None

    return None, None


def get_path_params(operation: dict, path: str, root: dict) -> dict:
    """
    Extrai parâmetros de path com prioridade:
      enum[0] → example no schema → example no param → tipo (uuid/int/str)
    Também captura placeholders {param} não declarados explicitamente.
    """
    result = {}
    for param in operation.get("parameters", []):
        if param.get("in") != "path":
            continue
        name   = param["name"]
        schema = resolve_schema(param.get("schema", {}), root)

        if "enum" in schema:
            result[name] = schema["enum"][0]
        elif "example" in schema:
            result[name] = schema["example"]
        elif "example" in param:
            result[name] = param["example"]
        elif schema.get("type") == "integer":
            result[name] = 1
        elif schema.get("format") in ("uuid", "UUID"):
            result[name] = "00000000-0000-0000-0000-000000000001"
        else:
            result[name] = f"exemplo_{name}"

    # Placeholders no path não declarados como parâmetros
    for placeholder in re.findall(r"\{(\w+)\}", path):
        if placeholder not in result:
            result[placeholder] = f"exemplo_{placeholder}"

    return result


# ─── Prompt compartilhado ─────────────────────────────────────────────────────

def build_prompt(method: str, path: str, schema: dict, path_params: dict) -> str:
    parts = [
        "Você é um gerador de dados de teste para APIs REST.",
        "Gere um JSON de teste realista para a requisição abaixo.",
        "",
        f"Endpoint: {method.upper()} {path}",
    ]

    if path_params:
        parts += [
            "",
            "Parâmetros de path (já resolvidos — NÃO inclua no body):",
            json.dumps(path_params, ensure_ascii=False, indent=2),
        ]

    if schema:
        parts += [
            "",
            "Schema do requestBody (resolvido):",
            json.dumps(schema, ensure_ascii=False, indent=2),
        ]

    parts += [
        "",
        "Regras:",
        "- Retorne APENAS o JSON do body, sem explicações, sem blocos markdown.",
        "- Use dados realistas em português brasileiro (nomes, emails, CPFs, telefones, URLs .gov.br ou .com.br).",
        "- Respeite tipos, enums e campos required do schema.",
        "- Campos nullable ou opcionais: inclua com null ou omita conforme o contexto.",
        "- Não inclua parâmetros de path, query ou headers no JSON.",
        "- Se não houver requestBody, retorne exatamente: {}",
    ]

    return "\n".join(parts)


def parse_llm_json(raw: str) -> dict:
    """Remove markdown fences e faz parse do JSON retornado pela LLM."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


# ─── Backend Claude ───────────────────────────────────────────────────────────

def make_claude_client(api_key: str):
    try:
        import anthropic
    except ImportError:
        print("❌ SDK do Claude não instalado. Execute: pip install anthropic")
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)



# ─── Backend LLM (Gatiator ou Ollama) ───────────────────────────────────────
import requests
def generate_via_llm(llm_url: str, model: str, backend: str,
                     method: str, path: str,
                     schema: dict | None, path_params: dict) -> dict:
    prompt = build_prompt(method, path, schema or {}, path_params)
    if backend == "ollama":
        # Garante que a URL termina com /api/generate
        if not llm_url.rstrip("/").endswith("api/generate"):
            llm_url = llm_url.rstrip("/") + "/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
    else:  # gatiator (OpenAI-like)
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
    headers = {"Content-Type": "application/json"}
    if backend == "gatiator":
        headers["Authorization"] = "Bearer qualquer"
    try:
        response = requests.post(llm_url, json=payload, headers=headers, timeout=60)
        if response.status_code != 200:
            raise RuntimeError(f"{response.status_code} {response.text[:300]}")
        data = response.json()
        if backend == "ollama":
            raw = data.get("response", "")
        else:
            raw = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        result = parse_llm_json(raw)
        if not result:
            raise RuntimeError("LLM retornou JSON vazio ou inválido")
        return result
    except Exception as e:
        raise RuntimeError(str(e)) from e


# ─── Nome do arquivo de saída ─────────────────────────────────────────────────

def make_filename(method: str, path: str) -> str:
    """
    POST /api/v1/contas/perfil/{perfil} → POST_api_v1_contas_perfil_X.json
    Garante que só parâmetros presentes no path sejam substituídos.
    """
    sanitized = path.lstrip("/")
    # Substitui apenas {param} do path por X
    sanitized = re.sub(r"\{[^}/]+\}", "X", sanitized)
    sanitized = re.sub(r"[/\\\s]+", "_", sanitized)
    sanitized = re.sub(r"[^a-zA-Z0-9_\-]", "", sanitized)
    return f"{method.upper()}_{sanitized}.json"


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():

    parser = argparse.ArgumentParser(
        description="Gera arquivos de dados de teste a partir do openapi.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python gerar_dados_exemplo.py openapi.json
  python gerar_dados_exemplo.py openapi.json --llm-backend ollama --llm-url http://localhost:11434/v1/chat/completions --llm-model llama3.2
  python gerar_dados_exemplo.py openapi.json --only-with-body --no-overwrite
        """
    )
    parser.add_argument("openapi", help="Caminho para o openapi.json")
    parser.add_argument("--llm-backend", choices=["gatiator", "ollama"], default=DEFAULT_BACKEND,
                        help="Backend LLM (sobrepõe LLM_BACKEND do .env). "
                             "gatiator → porta 1313 | ollama → porta 11434")
    parser.add_argument("--llm-url", default=None,
                        help="URL do backend LLM. Se omitido, usa a URL padrão do backend escolhido.")
    parser.add_argument("--llm-model", default=DEFAULT_MODEL,
                        help=f"Modelo LLM a usar. Default: {DEFAULT_MODEL}")
    parser.add_argument("--output-dir", default="output/tests/dados",
                        help="Diretório de saída. Default: output/tests/dados")
    parser.add_argument("--only-with-body", action="store_true",
                        help="Gera apenas para endpoints com requestBody")
    parser.add_argument("--no-overwrite", action="store_true",
                        help="Não sobrescreve arquivos existentes (default: sobrescreve)")
    args = parser.parse_args()

    # URL efetiva: argumento explícito tem prioridade; senão usa o mapa de backend
    effective_url = args.llm_url or BACKEND_URLS[args.llm_backend]

    # ── Setup de diretórios ───────────────────────────────────────────────────
    openapi_path = Path(args.openapi).resolve()
    output_dir   = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"📄 OpenAPI  : {openapi_path}")
    print(f"🤖 LLM      : {args.llm_backend}  ({effective_url} | modelo: {args.llm_model})")
    print(f"📁 Saída    : {output_dir.resolve()}")
    print()

    root  = load_openapi(str(openapi_path))
    paths = root.get("paths", {})

    total        = 0
    skipped      = 0
    from_example = 0
    from_llm     = 0
    errors       = 0


    HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            # Pula campos de metadados do path item e qualquer valor que não seja dict de operação
            if method.lower() not in HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                continue

            total += 1
            filename = make_filename(method, path)
            out_file = output_dir / filename

            if out_file.exists() and args.no_overwrite:
                print(f"  ⏭️  Já existe: {filename}")
                skipped += 1
                continue

            schema, example = get_request_body_info(operation, root)
            has_body = bool(schema or example)

            if args.only_with_body and not has_body:
                print(f"  ⏭️  Sem body : {method.upper()} {path}")
                skipped += 1
                continue

            path_params = get_path_params(operation, path, root)

            # ── Decisão: example do openapi ou LLM ───────────────────────────
            if example is not None:
                print(f"  📋 Example  : {method.upper()} {path}")
                body     = example if isinstance(example, dict) else {}
                used_llm = False
                from_example += 1
            else:
                print(f"  🤖 LLM ({args.llm_backend}): {method.upper()} {path}")
                try:
                    body = generate_via_llm(
                        effective_url, args.llm_model, args.llm_backend,
                        method, path, schema, path_params
                    )
                    time.sleep(RATE_LIMIT_DELAY)
                    used_llm = True
                    from_llm += 1
                except Exception as e:
                    print(f"    ❌ Erro LLM: {e}")
                    errors += 1
                    continue

            # ── Monta e persiste ──────────────────────────────────────────────
            result = {}
            if path_params:
                result["_path_params"] = path_params
            result.update(body)

            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            source = "LLM" if used_llm else "example"
            print(f"    ✅ [{source}] {out_file.name}")

    # ── Resumo ────────────────────────────────────────────────────────────────
    print()
    print("=" * 52)
    print(f"Total de endpoints  : {total}")
    print(f"📋 Via example      : {from_example}")
    print(f"🤖 Via LLM          : {from_llm}")
    print(f"⏭️  Pulados          : {skipped}")
    print(f"❌ Erros            : {errors}")
    print(f"📁 Saída            : {output_dir.resolve()}")


if __name__ == "__main__":
    main()