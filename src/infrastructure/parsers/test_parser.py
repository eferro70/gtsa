#!/usr/bin/env python3
import os
import sys
import json
import shutil
import argparse
import importlib
from datetime import datetime

def main():
    # 1. Argumentos de linha de comando
    parser_arg = argparse.ArgumentParser(description="Analisador de endpoints de API em projetos Node/TypeScript.")
    parser_arg.add_argument('-i', '--input', required=True, help='Caminho para a raiz do projeto Node/TypeScript')
    parser_arg.add_argument('--parser', default='ast_parser_node', help='Nome do arquivo do parser (sem .py)')
    args = parser_arg.parse_args()

    project_root = args.input
    parser_module_name = args.parser

    # Adiciona pasta de parsers ao sys.path
    PARSER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'parsers'))
    sys.path.insert(0, PARSER_DIR)

    # Importa o parser dinamicamente
    try:
        parser_module = __import__(parser_module_name)
        TSASTParser = getattr(parser_module, 'TSASTParser')
    except Exception as e:
        print(f"❌ Erro ao importar parser '{parser_module_name}': {e}")
        sys.exit(1)

    # ---------------------------------------------------------
    # ✅ LÓGICA SOLICITADA (Preservada integralmente)
    # ---------------------------------------------------------
    # Cria diretório de output/ast em ../../output/ast
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../output/ast'))
    if os.path.exists(base_dir):
        # Limpa apenas subdiretórios scan_* dentro de output/ast
        for item in os.listdir(base_dir):
            item_path = os.path.join(base_dir, item)
            if os.path.isdir(item_path) and item.startswith('scan_'):
                print(f"🗑️  Limpando diretório anterior: {item_path}")
                shutil.rmtree(item_path)
    os.makedirs(base_dir, exist_ok=True)
    # ---------------------------------------------------------

    # Cria subdiretório com timestamp para esta execução
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(base_dir, f"scan_{timestamp}")
    os.makedirs(session_dir, exist_ok=True)
    print(f"📁 Criado diretório para esta execução: {session_dir}")

    # Inicializa parser e contadores
    parser = TSASTParser(lang="typescript")
    total_files = 0
    total_endpoints = 0
    files_with_endpoints = []
    errors = []

    # Configurações de varredura
    IGNORE_DIRS = {'tests', 'test', 'node_modules', 'dist', 'build', 'coverage', '.git', '.nyc_output', 'out', 'tmp', 'swagger', 'migrations', 'seeders'}
    VALID_EXTENSIONS = {'.ts', '.tsx'}
    IGNORE_FILES = {'.d.ts'}
    error_log = os.path.join(session_dir, "errors.log")

    def safe_filename(path):
        return path.replace('/', '_').replace('\\', '_').replace(':', '_')

    # Varredura recursiva
    for root, dirs, files in os.walk(project_root):
        # Remove diretórios ignorados (modifica a lista in-place)
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            ext = os.path.splitext(file)[1]
            if ext not in VALID_EXTENSIONS:
                continue
            if any(file.endswith(ignore) for ignore in IGNORE_FILES):
                continue

            file_path = os.path.join(root, file)
            total_files += 1
            rel_path = os.path.relpath(file_path, project_root)
            safe_name = safe_filename(rel_path)
            output_file_path = os.path.join(session_dir, f"{safe_name}.json")

            print(f"\n📁 Analisando: {rel_path}")

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()

                endpoints = parser.extract_api_endpoints(code)
                valid_endpoints = [e for e in endpoints if not e['path'].startswith(('http://', 'https://'))]

                ast_tree = parser.parse_code(code)
                root_node = parser.get_root_node(code)

                file_data = {
                    "file": file_path,
                    "relative_path": rel_path,
                    "analyzed_at": datetime.now().isoformat(),
                    "endpoints_found": len(valid_endpoints),
                    "endpoints": valid_endpoints,
                    "ast_summary": {
                        "type": root_node.type,
                        "children_count": len(root_node.children),
                        "byte_range": [root_node.start_byte, root_node.end_byte],
                        "position": {
                            "start": {"line": root_node.start_point[0], "column": root_node.start_point[1]},
                            "end": {"line": root_node.end_point[0], "column": root_node.end_point[1]}
                        }
                    }
                }

                # default=str evita crash se a AST retornar objetos não serializáveis
                with open(output_file_path, "w", encoding="utf-8") as f:
                    json.dump(file_data, f, indent=2, ensure_ascii=False, default=str)

                if valid_endpoints:
                    total_endpoints += len(valid_endpoints)
                    files_with_endpoints.append({
                        'file': file_path,
                        'relative_path': rel_path,
                        'endpoints': valid_endpoints,
                        'output_file': output_file_path
                    })
                    print(f"  ✅ Encontrados {len(valid_endpoints)} endpoint(s)")
                else:
                    print(f"  ⚠️  Nenhum endpoint encontrado")

            except Exception as e:
                error_msg = f"Erro ao analisar {file_path}: {str(e)}"
                print(f"  ❌ {error_msg}")
                errors.append(error_msg)
                with open(error_log, "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now().isoformat()} - {error_msg}\n")

    # Gera resumo e relatórios
    summary = {
        "scan_info": {
            "timestamp": timestamp,
            "project_root": project_root,
            "total_files_analyzed": total_files,
            "files_with_endpoints": len(files_with_endpoints),
            "total_endpoints_found": total_endpoints,
            "errors_count": len(errors)
        },
        "endpoints_by_file": files_with_endpoints,
        "errors": errors
    }
    summary_file = os.path.join(session_dir, "summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

    report_file = os.path.join(session_dir, "REPORT.md")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# Relatório de Análise de API Endpoints\n\n")
        f.write(f"Data da análise: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Projeto: `{project_root}`\n\n")
        f.write("## Resumo\n\n")
        f.write(f"- 📁 Arquivos analisados: **{total_files}**\n")
        f.write(f"- 🎯 Arquivos com endpoints: **{len(files_with_endpoints)}**\n")
        f.write(f"- 🔗 Total de endpoints encontrados: **{total_endpoints}**\n")
        f.write(f"- ❌ Erros encontrados: **{len(errors)}**\n\n")
        if files_with_endpoints:
            f.write("## Endpoints Encontrados\n\n")
            for item in files_with_endpoints:
                f.write(f"### 📄 `{item['relative_path']}`\n\n")
                f.write("| Método | Path | Handler | Parâmetros |\n")
                f.write("|--------|------|---------|------------|\n")
                for ep in item['endpoints']:
                    params = ", ".join([p['name'] for p in ep['parameters']]) if ep['parameters'] else "-"
                    f.write(f"| {ep['method']} | `{ep['path']}` | `{ep['name']}` | {params} |\n")
                f.write("\n")
        if errors:
            f.write("## Erros Encontrados\n\n")
            for err in errors:
                f.write(f"- ❌ {err}\n")

    # Cria lista plana de endpoints
    all_flat = []
    for item in files_with_endpoints:
        for ep in item['endpoints']:
            all_flat.append({
                "file": item['relative_path'],
                "method": ep['method'],
                "path": ep['path'],
                "handler": ep['name'],
                "parameters": ep['parameters']
            })
    flat_file = os.path.join(session_dir, "all_endpoints.json")
    with open(flat_file, "w", encoding="utf-8") as f:
        json.dump(all_flat, f, indent=2, ensure_ascii=False, default=str)

    # Resumo no console
    print("\n" + "="*60)
    print("📊 RESUMO DA ANÁLISE")
    print("="*60)
    print(f"Arquivos analisados: {total_files}")
    print(f"Arquivos com endpoints: {len(files_with_endpoints)}")
    print(f"Total de endpoints encontrados: {total_endpoints}")
    print(f"Erros: {len(errors)}")
    print(f"\n📁 Resultados salvos em: {session_dir}")

if __name__ == "__main__":
    main()