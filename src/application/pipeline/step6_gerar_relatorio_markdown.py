#!/usr/bin/env python3
"""
step6_gerar_relatorio_markdown.py
-------------------------------------------
Gera relatório preciso a partir dos resultados do Schemathesis.

Agora parseia corretamente:
- JUnit XML para contagem real de testes
- Log do Schemathesis para estatísticas detalhadas
- Summary final do Schemathesis
"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configurações — resolvidas dinamicamente no main()
OUTPUT_DIR: Path = Path("output")
JUNIT_XML: Path = OUTPUT_DIR / "schemathesis_results.xml"
SCHEMATHESIS_LOG: Path = OUTPUT_DIR / "schemathesis.log"
HIGH_RISK_SPEC: Path = OUTPUT_DIR / "openapi_high_risk.json"
SUMMARY_MD: Path = OUTPUT_DIR / "test_api_summary.md"


class SchemathesisReportParser:
    """Parser corrigido para relatório do Schemathesis"""
    
    def __init__(self):
        self.results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'skipped': 0,
            'duration_seconds': 0,
            'endpoints_tested': 0,
            'endpoints_errored': 0,
            'endpoints_skipped': 0,
            'filtered_to_high_risk': False,
            'filtered_endpoints_count': 0,
            'failures_by_type': defaultdict(int),
            'endpoints': defaultdict(lambda: {
                'method': '',
                'path': '',
                'tests': 0,
                'passed': 0,
                'failed': 0,
                'errors': 0,
                'failures': []
            }),
            'schemathesis_summary': {}
        }
    
    def parse_junit_xml(self):
        """Parse JUnit XML para detalhamento por endpoint.

        IMPORTANTE: O Schemathesis gera 1 <testcase> por OPERAÇÃO (endpoint), não por
        caso de teste individual. Um endpoint com qualquer falha é marcado como failure
        mesmo que alguns casos passem. Por isso NÃO usamos os atributos tests/failures
        do <testsuite> para calcular taxa de sucesso — esses números vêm do log do
        Schemathesis via parse_schemathesis_log().
        """
        if not JUNIT_XML.exists():
            print(f"⚠️  JUnit XML não encontrado: {JUNIT_XML}")
            return

        try:
            tree = ET.parse(JUNIT_XML)
            root = tree.getroot()

            testsuite = root.find('.//testsuite')
            if testsuite is not None:
                self.results['duration_seconds'] = float(testsuite.get('time', 0))
                # NÃO lemos tests/failures/skipped do testsuite aqui:
                # esses valores representam operações, não casos de teste.

            # Parse por endpoint — usado apenas para o detalhamento qualitativo
            for testcase in root.findall('.//testcase'):
                classname = testcase.get('classname', 'unknown')
                name = testcase.get('name', 'unknown')

                if ' ' in classname:
                    method, path = classname.split(' ', 1)
                else:
                    method, path = '', classname

                key = f"{method} {path}"
                self.results['endpoints'][key]['method'] = method
                self.results['endpoints'][key]['path'] = path
                self.results['endpoints'][key]['tests'] += 1

                failure = testcase.find('failure')
                error   = testcase.find('error')

                if failure is None and error is None:
                    self.results['endpoints'][key]['passed'] += 1
                elif failure is not None:
                    self.results['endpoints'][key]['failed'] += 1
                    failure_msg = failure.get('message', 'Sem mensagem')
                    self.results['endpoints'][key]['failures'].append({
                        'test': name,
                        'message': failure_msg[:500]
                    })

                    # Classifica tipo de falha
                    if 'Server error' in failure_msg or '500' in failure_msg:
                        self.results['failures_by_type']['server_error'] += 1
                    elif 'Missing header' in failure_msg:
                        self.results['failures_by_type']['missing_header'] += 1
                    elif 'violates schema' in failure_msg:
                        self.results['failures_by_type']['schema_violation'] += 1
                    elif 'rejected schema-compliant' in failure_msg:
                        self.results['failures_by_type']['rejected_valid'] += 1
                    elif 'Undocumented HTTP status' in failure_msg:
                        self.results['failures_by_type']['undocumented_status'] += 1
                    elif 'accepts invalid authentication' in failure_msg:
                        self.results['failures_by_type']['auth_issue'] += 1
                    else:
                        self.results['failures_by_type']['other'] += 1
                elif error is not None:
                    self.results['endpoints'][key]['errors'] += 1

        except Exception as e:
            print(f"❌ Erro ao parsear JUnit: {e}")
    
    def parse_schemathesis_log(self):
        """Parse do log do Schemathesis para o summary.

        Fonte de verdade para contagem de casos de teste:
          - 'Test cases: N generated, M found K unique failures'
          - Fases: 'Fuzzing (in Xs)' com '✅ P passed  ❌ F failed'
          - Fases skipped: '⏭  Examples'

        O JUnit XML conta operações (endpoints), não casos de teste —
        por isso as métricas globais de passed/failed vêm daqui.
        """
        if not SCHEMATHESIS_LOG.exists():
            print(f"⚠️  Log não encontrado: {SCHEMATHESIS_LOG}")
            return

        with open(SCHEMATHESIS_LOG, 'r', encoding='utf-8') as f:
            content = f.read()

        # --- Sumário de casos de teste (linha final) ---
        summary_match = re.search(
            r'Test cases:\s+(\d+)\s+generated,\s+(\d+)\s+found\s+(\d+)\s+unique\s+failures',
            content
        )
        if summary_match:
            generated      = int(summary_match.group(1))
            found_with_fail = int(summary_match.group(2))
            unique_failures = int(summary_match.group(3))
            self.results['schemathesis_summary'] = {
                'generated': generated,
                'found': found_with_fail,
                'unique_failures': unique_failures,
            }

        # --- Fases: passed/failed por fase ---
        # Exemplo: "✅ 2 passed  ❌ 4 failed"  (na seção Fuzzing)
        # Exemplo: "❌ 6 failed"               (na seção Coverage)
        phase_passed = 0
        phase_failed = 0
        phase_skipped = 0

        for m in re.finditer(r'✅\s+(\d+)\s+passed', content):
            phase_passed += int(m.group(1))
        for m in re.finditer(r'❌\s+(\d+)\s+failed', content):
            phase_failed += int(m.group(1))
        for m in re.finditer(r'⏭\s+(\d+)\s+skipped', content):
            phase_skipped += int(m.group(1))

        # Guarda para uso em generate_markdown()
        self.results['phase_passed']  = phase_passed
        self.results['phase_failed']  = phase_failed
        self.results['phase_skipped'] = phase_skipped

        # --- Operações selecionadas/testadas ---
        operations_match = re.search(
            r'Selected:\s+(\d+)/(\d+)\s+Tested:\s+(\d+)(?:\s+Errored:\s+(\d+))?(?:\s+Skipped:\s+(\d+))?',
            content
        )
        if operations_match:
            self.results['endpoints_selected'] = int(operations_match.group(1))
            self.results['endpoints_total_spec'] = int(operations_match.group(2))
            self.results['endpoints_tested']  = int(operations_match.group(3))
            self.results['endpoints_errored'] = int(operations_match.group(4) or 0)
            self.results['endpoints_skipped'] = int(operations_match.group(5) or 0)

        # --- Falhas por tipo (seção Failures: do summary) ---
        failures_section = re.search(r'Failures:\s+(.+?)(?=\n\n|\Z)', content, re.DOTALL)
        if failures_section:
            for line in failures_section.group(1).split('\n'):
                match = re.match(r'\s*❌\s+(.+?):\s+(\d+)', line)
                if match:
                    failure_type = match.group(1)
                    count = int(match.group(2))
                    if 'Server error' in failure_type:
                        self.results['failures_by_type']['server_error'] = count
                    elif 'Missing header' in failure_type:
                        self.results['failures_by_type']['missing_header'] = count
                    elif 'violates schema' in failure_type:
                        self.results['failures_by_type']['schema_violation'] = count
                    elif 'rejected schema-compliant' in failure_type:
                        self.results['failures_by_type']['rejected_valid'] = count
                    elif 'Undocumented HTTP status' in failure_type:
                        self.results['failures_by_type']['undocumented_status'] = count
                    elif 'accepts invalid authentication' in failure_type:
                        self.results['failures_by_type']['auth_issue'] = count
                    elif 'Unsupported methods' in failure_type:
                        self.results['failures_by_type']['unsupported_methods'] = count

        # --- Erros de schema ---
        errors_match = re.search(r'Errors:\s+🚫\s+Schema Error:\s+(\d+)', content)
        if errors_match:
            self.results['schema_errors'] = int(errors_match.group(1))
    
    def check_if_filtered(self):
        """Verifica se houve filtragem por alto risco"""
        if HIGH_RISK_SPEC.exists():
            try:
                with open(HIGH_RISK_SPEC, 'r') as f:
                    spec = json.load(f)
                    paths = spec.get('paths', {})
                    if paths:
                        self.results['filtered_to_high_risk'] = True
                        self.results['filtered_endpoints_count'] = len(paths)
            except Exception:
                pass
    
    def generate_markdown(self):
        """Gera relatório Markdown corrigido"""
        
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(SUMMARY_MD, 'w', encoding='utf-8') as f:
            # Cabeçalho
            f.write("# 🔒 Relatório de Testes Schemathesis\n\n")
            f.write(f"*Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            
            # Configuração
            f.write("## ⚙️ Configuração dos Testes\n\n")
            if self.results.get('filtered_to_high_risk'):
                f.write(f"⚠️ **Teste restrito a alto risco**: Apenas endpoints com classificação **alto risco** foram testados.\n")
                f.write(f"   - Endpoints de alto risco: {self.results.get('filtered_endpoints_count', 0)}\n\n")
            else:
                f.write("✅ **Teste completo**: Todos os endpoints da OpenAPI spec foram testados.\n\n")
            
            # Resumo Geral
            f.write("## 📊 Resumo Geral dos Testes\n\n")

            # Fonte de verdade: log do Schemathesis (fases + sumário final).
            # O JUnit XML conta 1 testcase por OPERAÇÃO e marca qualquer operação
            # com ≥1 falha como failure — não reflete a contagem real de casos.
            summary = self.results.get('schemathesis_summary', {})
            total   = summary.get('generated', 0)

            # passed/failed por fase (✅ N passed / ❌ N failed no log)
            phase_passed  = self.results.get('phase_passed', 0)
            phase_failed  = self.results.get('phase_failed', 0)
            phase_skipped = self.results.get('phase_skipped', 0)

            # Se não conseguimos extrair fases, usa unique_failures como estimativa
            if phase_passed == 0 and phase_failed == 0 and total > 0:
                unique_failures = summary.get('unique_failures', 0)
                phase_failed = unique_failures
                phase_passed = total - unique_failures

            passed  = phase_passed
            failed  = phase_failed
            skipped = phase_skipped
            errors  = self.results.get('schema_errors', 0)
            success_rate = (passed / (passed + failed) * 100) if (passed + failed) > 0 else 0
            
            f.write("| Métrica | Valor |\n")
            f.write("|---------|-------|\n")
            f.write(f"| **Total de casos de teste gerados** | **{total:,}** |\n")
            f.write(f"| ✅ Testes bem-sucedidos | {passed:,} |\n")
            f.write(f"| ❌ Testes com falha | {failed:,} |\n")
            f.write(f"| ⚠️ Erros de schema | {errors} |\n")
            f.write(f"| ⏭️ Testes ignorados | {skipped} |\n")
            f.write(f"| **Taxa de sucesso** | **{success_rate:.1f}%** |\n")
            
            if self.results['duration_seconds'] > 0:
                f.write(f"| ⏱️ Duração total | {self.results['duration_seconds']:.2f}s |\n")
            
            f.write("\n")
            
            # Estatísticas de endpoints
            f.write("## 🎯 Cobertura de Endpoints\n\n")
            f.write("| Métrica | Valor |\n")
            f.write("|---------|-------|\n")
            f.write(f"| Total de operações na spec | {self.results.get('endpoints_total_spec', self.results.get('endpoints_tested', 0) + self.results.get('endpoints_errored', 0) + self.results.get('endpoints_skipped', 0))} |\n")
            f.write(f"| ✅ Endpoints testados | {self.results.get('endpoints_tested', 0)} |\n")
            f.write(f"| ⚠️ Endpoints com erro | {self.results.get('endpoints_errored', 0)} |\n")
            f.write(f"| ⏭️ Endpoints ignorados | {self.results.get('endpoints_skipped', 0)} |\n")
            f.write("\n")
            
            # Tipos de Falha
            f.write("## 🔍 Tipos de Falha Encontrados\n\n")
            f.write("| Tipo de Falha | Quantidade | Severidade |\n")
            f.write("|---------------|------------|------------|\n")
            
            failure_types = {
                'server_error': ('Erro interno do servidor (500)', '🔴 Alta'),
                'missing_header': ('Header obrigatório ausente não rejeitado', '🔴 Alta'),
                'auth_issue': ('Aceita autenticação inválida', '🔴 Alta'),
                'rejected_valid': ('Rejeita requisição válida (falso positivo)', '🟠 Média'),
                'schema_violation': ('Resposta viola schema documentado', '🟠 Média'),
                'undocumented_status': ('Status HTTP não documentado', '🟡 Baixa'),
                'unsupported_methods': ('Métodos não suportados (ex: TRACE)', '🟡 Baixa'),
                'other': ('Outras falhas', '🟡 Baixa')
            }
            
            for key, (label, severity) in failure_types.items():
                count = self.results['failures_by_type'].get(key, 0)
                if count > 0:
                    f.write(f"| {label} | {count} | {severity} |\n")
            
            f.write("\n")
            
            # Detalhamento de falhas por endpoint (top 10)
            if self.results['endpoints']:
                f.write("## 📋 Detalhamento por Endpoint (Top 10 com mais falhas)\n\n")
                f.write("| Método | Endpoint | Testes | ✅ | ❌ | ⚠️ |\n")
                f.write("|--------|----------|--------|----|----|-----|\n")
                
                # Ordena por número de falhas
                sorted_endpoints = sorted(
                    self.results['endpoints'].items(),
                    key=lambda x: x[1]['failed'],
                    reverse=True
                )[:10]
                
                for key, info in sorted_endpoints:
                    if info['method'] and info['path']:
                        f.write(f"| {info['method']} | `{info['path'][:50]}` | {info['tests']} | ")
                        f.write(f"{info['passed']} | {info['failed']} | {info['errors']} |\n")
                
                f.write("\n")
            
            # Principais falhas
            f.write("## 🐛 Principais Falhas Encontradas\n\n")
            
            all_failures = []
            for info in self.results['endpoints'].values():
                all_failures.extend(info['failures'])
            
            # Mostra primeiras 10 falhas
            for i, failure in enumerate(all_failures[:10], 1):
                f.write(f"**{i}. {failure['test']}**\n\n")
                f.write(f"```\n{failure['message'][:300]}\n```\n\n")
            
            if len(all_failures) > 10:
                f.write(f"*... e mais {len(all_failures) - 10} falhas*\n\n")
            
            # Recomendações
            f.write("## 💡 Recomendações\n\n")
            
            if self.results['failures_by_type'].get('server_error', 0) > 0:
                f.write("### 🔴 Críticas (Corrigir Imediatamente)\n\n")
                f.write("1. **Erros internos do servidor (500)** - API está quebrando com entradas válidas\n")
                f.write("   - Verifique logs do servidor para stack traces\n")
                f.write("   - Adicione tratamento de exceções nos endpoints\n")
                f.write("   - Valide inputs antes de processar\n\n")
            
            if self.results['failures_by_type'].get('auth_issue', 0) > 0:
                f.write("### 🟠 Segurança\n\n")
                f.write("1. **Falhas de autenticação** - Endpoints aceitando tokens inválidos\n")
                f.write("   - Implemente validação rigorosa de tokens JWT\n")
                f.write("   - Retorne 401 para credenciais inválidas\n\n")
            
            if self.results['failures_by_type'].get('schema_violation', 0) > 0:
                f.write("### 🟡 Documentação\n\n")
                f.write("1. **Inconsistências de schema** - Respostas não correspondem à documentação\n")
                f.write("   - Atualize a OpenAPI spec para refletir a implementação real\n")
                f.write("   - Ou corrija a implementação para seguir a spec\n\n")
            
            # Informações técnicas
            f.write("## 📁 Informações Técnicas\n\n")
            f.write(f"- **Arquivo de log:** `{SCHEMATHESIS_LOG}`\n")
            f.write(f"- **Relatório JUnit:** `{JUNIT_XML}`\n")
            if self.results.get('filtered_to_high_risk'):
                f.write(f"- **Spec filtrada:** `{HIGH_RISK_SPEC}`\n")
            f.write(f"- **Ferramenta:** [Schemathesis](https://schemathesis.readthedocs.io/)\n")
            f.write(f"- **Comando executado:** `schemathesis run --checks all --report junit`\n\n")
            
            f.write("*Relatório gerado automaticamente pelo pipeline de testes GTSA.*\n")
    
    def run(self):
        """Executa todo o pipeline"""
        print("📊 Gerando relatório a partir dos resultados do Schemathesis...")
        
        self.parse_junit_xml()
        self.parse_schemathesis_log()
        self.check_if_filtered()
        self.generate_markdown()
        
        # Estatísticas finais
        print(f"\n✅ Relatório gerado: {SUMMARY_MD}")
        print(f"\n📈 Resumo dos testes:")
        
        if self.results['total_tests'] > 0:
            print(f"   - Total de testes: {self.results['total_tests']:,}")
            print(f"   - ✅ Sucesso: {self.results['passed']:,}")
            print(f"   - ❌ Falhas: {self.results['failed']:,}")
        else:
            summary = self.results.get('schemathesis_summary', {})
            print(f"   - Total gerado: {summary.get('generated', 0):,}")
            print(f"   - ❌ Falhas únicas: {summary.get('unique_failures', 0)}")
        
        print(f"   - 📊 Cobertura: {self.results.get('endpoints_tested', 0)} endpoints testados")
        
        # Mostra principais problemas
        if self.results['failures_by_type'].get('server_error', 0) > 0:
            print(f"   - 🔴 {self.results['failures_by_type']['server_error']} erros 500 detectados")
        if self.results['failures_by_type'].get('auth_issue', 0) > 0:
            print(f"   - 🔴 {self.results['failures_by_type']['auth_issue']} falhas de autenticação")


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Gera relatório Markdown dos resultados do Schemathesis")
    ap.add_argument("--output-dir", "-d", default=None,
                    help="Diretório de saída (padrão: env REPORTS_DIR ou 'output')")
    ap.add_argument("--env-file", default=None,
                    help="Arquivo .env a carregar (ex: .env.neosigner)")
    ap.add_argument("--full",        action="store_true", help="Inclui todos os endpoints no relatório")
    ap.add_argument("--hide-success",action="store_true", help="Omite endpoints com sucesso")
    ap.add_argument("--hide-skip",   action="store_true", help="Omite endpoints pulados")
    args = ap.parse_args()

    # Carrega .env se informado
    if args.env_file:
        env_path = Path(args.env_file)
        if env_path.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_path, override=True)
            except ImportError:
                # fallback manual
                with open(env_path, encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            os.environ.setdefault(k.strip(), v.strip())

    # Resolve o diretório de saída
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    if args.output_dir:
        output_dir = Path(args.output_dir)
        if not output_dir.is_absolute():
            output_dir = project_root / args.output_dir
    else:
        env_output_dir = os.getenv("REPORTS_DIR", "output")
        output_dir = Path(env_output_dir)
        if not output_dir.is_absolute():
            output_dir = project_root / env_output_dir
    output_dir = output_dir.resolve()

    # Atualiza as constantes globais para que SchemathesisReportParser as use
    global OUTPUT_DIR, JUNIT_XML, SCHEMATHESIS_LOG, HIGH_RISK_SPEC, SUMMARY_MD
    OUTPUT_DIR       = output_dir
    JUNIT_XML        = output_dir / "schemathesis_results.xml"
    SCHEMATHESIS_LOG = output_dir / "schemathesis_execution.log"
    HIGH_RISK_SPEC   = output_dir / "openapi_high_risk.json"
    SUMMARY_MD       = output_dir / "test_api_summary.md"

    print(f"📁 Output dir: {output_dir}")

    parser = SchemathesisReportParser()
    parser.run()


if __name__ == "__main__":
    main()