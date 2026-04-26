"""
gerar_relatorio_markdown.py
---------------------------
Gera um relatório em Markdown com o resumo dos testes de API executados, a partir do log de execução.

Principais funções:
- Lê o arquivo de log dos testes automatizados.
- Extrai resultados de sucesso/falha por endpoint, método e role.
- Gera um arquivo Markdown com o resumo dos testes, cobertura e falhas.

Uso típico: python3 gerar_relatorio_markdown.py
"""

import re
import os
from collections import defaultdict

LOGFILE = "output/tests/test_api_llm.log"
SUMMARY_MD = "output/tests/test_api_llm_summary.md"

# ✅ POST /api/v1/foo (role: REQ)
# ❌ GET /api/v1/bar (role: REQ) [exit 1]
RE_ENDPOINT_RESULT = re.compile(
    r"^([✅❌])\s+(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(\S+)\s+\(role:\s*(\w+)\)"
)

# [INFO] ▶️ Iniciando testes para POST /api/v1/foo
RE_ENDPOINT_START = re.compile(
    r"▶️\s+Iniciando testes para\s+(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(\S+)"
)

# [INFO] 🧪 test_basic para GET /api/v1/foo
# [INFO] 🧪 test_multiple_examples: 5 exemplos para GET /api/v1/foo
# Extrai (test_name, method, path) diretamente da linha — tolerante a intercalação
RE_TEST_LINE = re.compile(
    r"🧪\s+(test_\w+)[^\n]*\bpara\s+(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(\S+)"
)

# [INFO] 📊 Cobertura automática: Testando endpoint POST /api/v1/foo
RE_COVERAGE = re.compile(
    r"📊 Cobertura automática.*?(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(\S+)"
)

endpoints = defaultdict(lambda: {
    "status": "",
    "tests": set(),
    "method": "",
    "path": "",
    "role": "",
    "has_coverage": False,
})

def parse_log():
    if not os.path.exists(LOGFILE):
        print(f"Arquivo de log não encontrado: {LOGFILE}")
        return

    with open(LOGFILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.rstrip("\n")

        # Resultado final do endpoint (escrito pelo shell)
        m = RE_ENDPOINT_RESULT.match(line)
        if m:
            symbol, method, path, role = m.groups()
            key = f"{method} {path}"
            endpoints[key]["method"] = method
            endpoints[key]["path"] = path
            endpoints[key]["role"] = role
            # Só atualiza status se ainda não tem ✅ (primeiro resultado vence)
            if not endpoints[key]["status"]:
                endpoints[key]["status"] = "✅" if symbol == "✅" else "❌"
            continue

        # Início de endpoint — garante que o endpoint existe no dict
        m = RE_ENDPOINT_START.search(line)
        if m:
            method, path = m.groups()
            key = f"{method} {path}"
            endpoints[key]["method"] = method
            endpoints[key]["path"] = path
            continue

        # Tipo de teste — extrai endpoint diretamente da linha
        m = RE_TEST_LINE.search(line)
        if m:
            test_name, method, path = m.groups()
            key = f"{method} {path}"
            endpoints[key]["method"] = method
            endpoints[key]["path"] = path
            endpoints[key]["tests"].add(test_name)
            continue

        # Cobertura automática — extrai endpoint diretamente da linha
        m = RE_COVERAGE.search(line)
        if m:
            method, path = m.groups()
            key = f"{method} {path}"
            endpoints[key]["has_coverage"] = True


def write_summary():

    TEST_TYPES = {
        "test_specific_data":         ("TS", "Teste com dados específicos"),
        "test_basic":                 ("TB", "Teste básico (dados mínimos)"),
        "test_property_based":        ("TP", "Teste property-based (Hypothesis)"),
        "test_multiple_examples":     ("TM", "Teste múltiplos exemplos aleatórios"),
        "test_response_schema":       ("TR", "Teste de schema de resposta"),
        "test_endpoint_without_body": ("SB", "Teste sem body (GET/DELETE)"),
        "test_no_generated":          ("TN", "Teste sem dados gerados (--no-generated)"),
    }

    # Mapeamento reverso para legenda
    CODE_TO_LABEL = {v[0]: v[1] for v in TEST_TYPES.values()}


    all_tests = set()
    for info in endpoints.values():
        all_tests.update(info["tests"])

    total         = len(endpoints)
    success_count = sum(1 for i in endpoints.values() if i["status"] == "✅")
    fail_count    = sum(1 for i in endpoints.values() if i["status"] == "❌")
    total_tests   = sum(len(i["tests"]) for i in endpoints.values())
    tests_tracked = len(all_tests) > 0
    has_coverage  = any(i["has_coverage"] for i in endpoints.values())



    with open(SUMMARY_MD, "w", encoding="utf-8") as f:
        f.write("# Relatório de Testes de API\n\n")

        f.write("## Tipos de Teste Executados\n\n")
        f.write("| Código | Tipo de Teste | Status |\n")
        f.write("|--------|-------------------------------|--------|\n")
        for test_key, (code, test_label) in TEST_TYPES.items():
            status = "✅" if test_key in all_tests else ("❌" if tests_tracked else "⚠️ não rastreado")
            f.write(f"| {code} | {test_label} | {status} |\n")
        coverage_status = "✅" if (has_coverage or total > 0) else "❌"
        f.write(f"| — | Cobertura automática de todos endpoints | {coverage_status} |\n\n")

        f.write("---\n\n")
        f.write("## Detalhamento por Endpoint\n\n")
        f.write("> **Legenda dos símbolos de status:**  ")
        f.write("✅ = sucesso, ❌ = falha, ⚠️ = status desconhecido/não registrado\n\n")
        f.write("| Método | Endpoint | Role | Testes Realizados | Status Final |\n")
        f.write("|--------|----------|------|-------------------|--------------|\n")
        for key, info in sorted(endpoints.items()):
            if info["tests"]:
                codes = [TEST_TYPES[t][0] if t in TEST_TYPES else t for t in sorted(info["tests"])]
                tests_str = ", ".join(codes)
            else:
                tests_str = "Nenhum identificado" if tests_tracked else "não rastreado"
            status = info["status"] or "⚠️"
            role   = info["role"] or "—"
            f.write(f"| {info['method']} | {info['path']} | {role} | {tests_str} | {status} |\n")

        f.write("\n---\n\n")
        f.write("## Estatísticas\n\n")
        f.write(f"- **Total de endpoints testados:** {total}\n")
        f.write(f"- **Total de tipos de teste rastreados:** {total_tests}\n")
        f.write(f"- **Endpoints com sucesso:** {success_count}\n")
        f.write(f"- **Endpoints com falha:** {fail_count}\n\n")
        f.write("*Relatório gerado automaticamente a partir do log de execução.*\n")


def main():
    parse_log()
    write_summary()
    print(f"✅ Relatório gerado em {SUMMARY_MD}")
    print(f"📊 Total de endpoints analisados: {len(endpoints)}")
    success = sum(1 for i in endpoints.values() if i["status"] == "✅")
    fail    = sum(1 for i in endpoints.values() if i["status"] == "❌")
    print(f"   ✅ Sucesso: {success}  ❌ Falha: {fail}")


if __name__ == "__main__":
    main()