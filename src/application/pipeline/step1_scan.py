#!/usr/bin/env python3
"""
step1_scan.py
-------------------
Script para análise estática de projetos, extraindo endpoints de APIs 
a partir do código-fonte via análise AST.

Suporta múltiplas linguagens através de parsers específicos.

Funcionalidades:
- Varre recursivamente o diretório informado
- Detecta automaticamente a linguagem do projeto
- Extrai endpoints via parser específico para cada linguagem
- Gera relatórios detalhados em JSON e Markdown

Parâmetros de linha de comando:
    -i, --input       Caminho para a raiz do projeto (obrigatório)
    --language        Linguagem do projeto (typescript, python, java, etc.)
    --output-dir      Diretório para relatórios (padrão: ../../../output)

Exemplo de uso:
    python3 step1_scan.py -i /caminho/para/projeto --language typescript
"""

import os
import sys
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Type

# Garante que a raiz do projeto esteja no sys.path para imports por pacote.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Importar parsers disponíveis
from src.infrastructure.parsers.base_parser import BaseParser

# Tentar importar parsers específicos, com fallback gentil
try:
    from src.infrastructure.parsers.ast_parser_typescript import TypeScriptParser
    PARSERS = {
        'typescript': TypeScriptParser,
        'javascript': TypeScriptParser,  # JavaScript usa mesmo parser
        'ts': TypeScriptParser,
        'js': TypeScriptParser,
    }
except ImportError as e:
    print(f"⚠️  Aviso: Não foi possível carregar o parser TypeScript: {e}")
    PARSERS = {}

# Constantes de varredura
IGNORE_DIRS = {
    'tests', 'test', '__tests__', '__test__',
    'node_modules', 'dist', 'build', 'coverage',
    '.git', '.nyc_output', 'out', 'tmp',
    'swagger', 'migrations', 'seeders', '__pycache__',
    'venv', 'env', '.venv', '.env', 'target',
}


def safe_filename(path: str) -> str:
    """Converte caminho para nome de arquivo seguro"""
    return path.replace('/', '_').replace('\\', '_').replace(':', '_')


def detect_project_language(project_path: str) -> Optional[str]:
    """
    Detecta automaticamente a linguagem principal do projeto
    baseado em arquivos de configuração e extensões comuns
    """
    indicators = {
        'typescript': ['tsconfig.json', 'package.json', '.ts', '.tsx'],
        'python': ['requirements.txt', 'setup.py', 'pyproject.toml', '.py'],
        'java': ['pom.xml', 'build.gradle', '.java'],
        'go': ['go.mod', 'go.sum', '.go'],
        'ruby': ['Gemfile', 'Rakefile', '.rb'],
    }
    
    scores = {lang: 0 for lang in indicators}
    
    for root, dirs, files in os.walk(project_path):
        # Limita profundidade para não varrer tudo
        if root.count(os.sep) - project_path.count(os.sep) > 2:
            continue
            
        for file in files:
            for lang, patterns in indicators.items():
                if file in patterns[:3]:  # Arquivos de configuração
                    scores[lang] += 10
                if any(file.endswith(ext) for ext in patterns[2:]):  # Extensões
                    scores[lang] += 1
        
        # Para se já tiver um candidato forte
        if max(scores.values()) > 20:
            break
    
    if max(scores.values()) > 0:
        detected = max(scores, key=scores.get)
        print(f"🔍 Linguagem detectada: {detected}")
        return detected
    
    return None


def get_parser_for_language(language: str) -> Optional[BaseParser]:
    """Retorna o parser apropriado para a linguagem"""
    if language not in PARSERS:
        print(f"❌ Parser não encontrado para linguagem: {language}")
        print(f"   Parsers disponíveis: {list(PARSERS.keys())}")
        return None
    
    parser_class = PARSERS[language]
    return parser_class()


def analyze_project(
    project_path: str, 
    language: Optional[str] = None,
    output_dir: Optional[str] = None
) -> Dict:
    """
    Analisa projeto e extrai endpoints
    
    Args:
        project_path: Caminho do projeto
        language: Linguagem do projeto (se None, tenta detectar)
        output_dir: Diretório de saída para relatórios
    
    Returns:
        Dicionário com resultados da análise
    """
    
    # Detecta ou valida linguagem
    if language is None:
        language = detect_project_language(project_path)
        if language is None:
            raise ValueError("Não foi possível detectar a linguagem do projeto. Especifique com --language")
    
    # Obtém parser
    parser = get_parser_for_language(language)
    if parser is None:
        raise ValueError(f"Parser não disponível para linguagem: {language}")
    
    print(f"🚀 Iniciando análise do projeto: {project_path}")
    print(f"📝 Linguagem: {language}")
    
    # -- diretório base de testes -----------------------------------------------
    base_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../../../src/application/pipeline/tests')
    )
    if os.path.exists(base_dir):
        for item in os.listdir(base_dir):
            item_path = os.path.join(base_dir, item)
            if os.path.isdir(item_path) and item.startswith('scan_'):
                print(f"🗑️  Limpando diretório anterior: {item_path}")
                shutil.rmtree(item_path)
    os.makedirs(base_dir, exist_ok=True)

    # -- diretório com timestamp ------------------------------------------------
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(base_dir, f"scan_{timestamp}_{language}")
    os.makedirs(session_dir, exist_ok=True)
    print(f"📁 Criado diretório para esta execução: {session_dir}")

    # -- diretório de output geral ----------------------------------------------
    if output_dir is None:
        output_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '../../../output')
        )
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Limpa arquivos antigos
    for old in Path(output_dir).glob("*_endpoints.json"):
        old.unlink(missing_ok=True)
    for old in Path(output_dir).glob("*_relatorio_api.md"):
        old.unlink(missing_ok=True)

    # -- inicializa contadores --------------------------------------------------
    total_files = 0
    total_endpoints = 0
    files_with_endpoints: List[Dict] = []
    all_flat: List[Dict] = []
    errors: List[str] = []
    error_log = os.path.join(session_dir, "errors.log")

    # ---------------------------------------------------------------------------
    # Varredura recursiva
    # ---------------------------------------------------------------------------
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, project_path)
            
            # Verifica se o parser suporta este arquivo
            if not parser.supports_file(file_path):
                continue
            
            output_file_path = os.path.join(session_dir, f"{safe_filename(rel_path)}.json")
            total_files += 1

            print(f"\n📁 Analisando: {rel_path}")

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()

                # Extrai endpoints usando o parser específico
                raw_endpoints = parser.extract_api_endpoints(code, file_path=rel_path)
                
                # Filtra URLs externas
                valid_endpoints = [
                    e for e in raw_endpoints
                    if not e['path'].startswith(('http://', 'https://'))
                ]

                # Obtém resumo da AST
                ast_summary = parser.get_ast_summary(code)

                file_data = {
                    "file": file_path,
                    "relative_path": rel_path,
                    "analyzed_at": datetime.now().isoformat(),
                    "endpoints_found": len(valid_endpoints),
                    "endpoints": valid_endpoints,
                    "ast_summary": ast_summary,
                    "language": language,
                }
                
                with open(output_file_path, "w", encoding="utf-8") as f:
                    json.dump(file_data, f, indent=2, ensure_ascii=False, default=str)

                if valid_endpoints:
                    total_endpoints += len(valid_endpoints)
                    files_with_endpoints.append({
                        'file': file_path,
                        'relative_path': rel_path,
                        'endpoints': valid_endpoints,
                        'output_file': output_file_path,
                    })
                    
                    for ep in valid_endpoints:
                        all_flat.append({
                            "file": rel_path,
                            "method": ep['method'],
                            "path": ep['path'],
                            "handler": ep['name'],
                            "parameters": ep['parameters'],
                            "line_number": ep.get('line_number'),
                            "context": ep.get('context'),
                        })
                    
                    print(f"  ✅ Encontrados {len(valid_endpoints)} endpoint(s)")
                    for ep in valid_endpoints[:3]:
                        print(f"     • {ep['method']} {ep['path']} -> {ep['name']}")
                    if len(valid_endpoints) > 3:
                        print(f"     ... e mais {len(valid_endpoints) - 3}")
                else:
                    print(f"  ⚠️  Nenhum endpoint encontrado")

            except Exception as e:
                error_msg = f"Erro ao analisar {file_path}: {str(e)}"
                print(f"  ❌ {error_msg}")
                errors.append(error_msg)
                with open(error_log, "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now().isoformat()} - {error_msg}\n")

    # ---------------------------------------------------------------------------
    # Saídas — session_dir
    # ---------------------------------------------------------------------------

    summary = {
        "scan_info": {
            "timestamp": timestamp,
            "project_root": project_path,
            "language": language,
            "total_files_analyzed": total_files,
            "files_with_endpoints": len(files_with_endpoints),
            "total_endpoints_found": total_endpoints,
            "errors_count": len(errors),
        },
        "endpoints_by_file": files_with_endpoints,
        "errors": errors,
    }
    
    with open(os.path.join(session_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

    with open(os.path.join(session_dir, "all_endpoints.json"), "w", encoding="utf-8") as f:
        json.dump(all_flat, f, indent=2, ensure_ascii=False, default=str)

    # Gera relatório Markdown
    with open(os.path.join(session_dir, "REPORT.md"), "w", encoding="utf-8") as f:
        f.write(f"# Relatório de Análise de API Endpoints\n\n")
        f.write(f"Data da análise: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Projeto: `{project_path}`\n")
        f.write(f"Linguagem: `{language}`\n\n")
        f.write("## Resumo\n\n")
        f.write(f"- 📁 Arquivos analisados: **{total_files}**\n")
        f.write(f"- 🎯 Arquivos com endpoints: **{len(files_with_endpoints)}**\n")
        f.write(f"- 🔗 Total de endpoints encontrados: **{total_endpoints}**\n")
        f.write(f"- ❌ Erros encontrados: **{len(errors)}**\n\n")
        
        if files_with_endpoints:
            f.write("## Endpoints Encontrados\n\n")
            for item in files_with_endpoints:
                f.write(f"### 📄 `{item['relative_path']}`\n\n")
                f.write("| Método | Path | Handler | Linha | Parâmetros |\n")
                f.write("|--------|------|---------|-------|------------|\n")
                for ep in item['endpoints']:
                    params = ", ".join(p['name'] for p in ep['parameters']) if ep['parameters'] else "-"
                    f.write(f"| {ep['method']} | `{ep['path']}` | `{ep['name']}` | {ep.get('line_number', '-')} | {params} |\n")
                f.write("\n")
        
        if errors:
            f.write("## Erros Encontrados\n\n")
            for err in errors:
                f.write(f"- ❌ {err}\n")

    # ---------------------------------------------------------------------------
    # Saídas de compatibilidade
    # ---------------------------------------------------------------------------

    with open(Path(base_dir) / f"regular_endpoints_{language}.json", "w", encoding="utf-8") as f:
        json.dump(all_flat, f, indent=2, ensure_ascii=False)

    methods_count: Dict[str, int] = {}
    for ep in all_flat:
        methods_count[ep['method']] = methods_count.get(ep['method'], 0) + 1

    with open(Path(output_dir) / f"api_analyse_report_{language}.md", "w", encoding="utf-8") as f:
        f.write(f"# Relatório de Análise de API - {language}\n\n")
        f.write("## Resumo\n\n")
        f.write(f"- **Total de endpoints encontrados:** {len(all_flat)}\n")
        if all_flat:
            f.write(f"- **Métodos HTTP:** {', '.join(sorted(methods_count))}\n")
        f.write("\n## Endpoints por Método\n\n")
        for method, count in sorted(methods_count.items()):
            f.write(f"- **{method}:** {count}\n")
        f.write("\n## Lista de Endpoints\n\n")
        f.write("| Método | Path | Handler | Arquivo | Linha |\n")
        f.write("|--------|------|---------|---------|-------|\n")
        for ep in sorted(all_flat, key=lambda x: (x['method'], x['path'])):
            f.write(f"| {ep['method']} | `{ep['path']}` | `{ep['handler']}` | {ep['file']} | {ep.get('line_number', '-')} |\n")

    # ---------------------------------------------------------------------------
    # Resumo no console
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("📊 RESUMO DA ANÁLISE")
    print("=" * 60)
    print(f"Linguagem:                    {language}")
    print(f"Arquivos analisados:          {total_files}")
    print(f"Arquivos com endpoints:       {len(files_with_endpoints)}")
    print(f"Total de endpoints:           {total_endpoints}")
    print(f"Erros:                        {len(errors)}")
    print(f"\n📁 Resultados em:             {session_dir}")
    print(f"📄 regular_endpoints.json:    {base_dir}/regular_endpoints_{language}.json")
    print(f"📄 api_analyse_report.md:     {output_dir}/api_analyse_report_{language}.md")
    
    return summary


def main():
    arg_parser = argparse.ArgumentParser(
        description="Analisador universal de endpoints de API em projetos multi-linguagem."
    )
    arg_parser.add_argument('-i', '--input', required=True,
                            help='Caminho para a raiz do projeto')
    arg_parser.add_argument('--language', default=None,
                            help='Linguagem do projeto (typescript, python, java, etc.)')
    arg_parser.add_argument('--output-dir', default=None,
                            help='Diretório para relatórios (padrão: ../../../output)')
    args = arg_parser.parse_args()

    try:
        analyze_project(args.input, args.language, args.output_dir)
    except Exception as e:
        print(f"❌ Erro durante a análise: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()