#!/usr/bin/env python3
"""
step5_analyzer.py
--------------------
Script para análise de risco e enriquecimento de endpoints de API utilizando LLM local (Ollama ou Gatiator).

Funcionalidades:
- Lê um arquivo all_endpoints.json gerado por etapas anteriores.
- Envia os endpoints para um modelo LLM local para análise de risco, identificação de dados sensíveis (PII), sugestões de segurança e enriquecimento de metadados.
- Suporta fallback entre backends (Gatiator e Ollama) e prompts customizados.
- Gera relatórios enriquecidos em JSON e Markdown.

Parâmetros de linha de comando:
    <input_json>   Caminho para o arquivo all_endpoints.json a ser analisado (obrigatório)
    [opções]       Parâmetros opcionais para modelo, backend, etc.

Exemplo de uso:
        python3 step5_analyzer.py output/scan_20260425_143917/all_endpoints.json

Saídas:
- src/application/pipeline/tests/enriched_endpoints.json   (endpoints enriquecidos)
- output/enriched_endpoints_report.md    (relatório detalhado)
"""

import json
import requests
import os
import time
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

# Carrega variáveis do .env automaticamente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv não instalado. Variáveis do .env não serão carregadas automaticamente.")


class LocalLLMAnalyzer:
    def __init__(self, model: str = "codellama:7b", backend: str = "gatiator", llm_url: str = None):
        """
        Inicializa o analisador com backend LLM (ai-gatiator ou Ollama)
        Args:
            model: Nome do modelo
            backend: "gatiator" (padrão) ou "ollama"
            llm_url: URL customizada do backend (opcional)
        """
        self.model = model
        self.backend = backend
        
        # Define URL baseada no backend ou usa URL customizada
        if llm_url:
            self.llm_url = llm_url
        elif backend == "gatiator":
            self.llm_url = os.getenv("LLM_BASE_URL", "http://localhost:1313/v1/chat/completions")
        elif backend == "ollama":
            self.llm_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1/chat/completions")
        else:
            raise ValueError(f"Backend LLM desconhecido: {backend}")
    
    def _get_pii_patterns(self):
        """Tenta carregar padrões PII de pii_patterns.json na raiz do projeto, senão usa lista padrão."""
        try:
            patterns_path = Path(__file__).parent.parent.parent / "pii_patterns.json"
            if patterns_path.exists():
                with open(patterns_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️  Erro ao carregar pii_patterns.json: {e}")
        return ['cpf', 'cnpj', 'email', 'telefone', 'celular', 'nome', 'documento']

    def _simple_heuristic_analysis(self, endpoint: Dict) -> Dict:
        """Análise heurística simples (fallback quando LLM falha)"""
        path = endpoint.get('path', '').lower()
        method = endpoint.get('method', '').upper()

        # Detecta PII por padrões no path
        pii_fields = []
        pii_patterns = self._get_pii_patterns()
        for pattern in pii_patterns:
            if pattern in path:
                pii_fields.append(pattern)
        
        # Detecta autenticação necessária
        auth_required = True
        auth_type = "jwt"
        if 'public' in path or 'health' in path or 'metrics' in path or 'swagger' in path:
            auth_required = False
            auth_type = "none"
        elif 'login' in path or 'auth' in path:
            auth_type = "basic"
        
        # Detecta nível de risco
        risk_level = "baixo"
        risk_reason = "Endpoint sem dados sensíveis aparentes"
        
        if pii_fields:
            risk_level = "alto"
            risk_reason = f"Contém dados PII: {', '.join(pii_fields)}"
        elif method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            risk_level = "médio"
            risk_reason = "Método que modifica dados"
        elif ':id' in path or ':perfil' in path:
            risk_level = "médio"
            risk_reason = "Contém parâmetro de ID (possível BOLA)"
        
        # Detecta possíveis vulnerabilidades
        vulnerabilities = []
        if ':id' in path:
            vulnerabilities.append("bola")
        if method in ['POST', 'PUT'] and 'auth' not in path:
            vulnerabilities.append("injection")
        if not auth_required and method in ['POST', 'PUT', 'DELETE']:
            vulnerabilities.append("broken_auth")
        
        # Calcula score de risco (0-1)
        risk_score = 0.0
        if risk_level == "alto":
            risk_score = 0.9
        elif risk_level == "médio":
            risk_score = 0.5
        else:
            risk_score = 0.1
        
        return {
            "pii_fields": pii_fields,
            "auth_required": auth_required,
            "auth_type": auth_type,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_reason": risk_reason,
            "vulnerabilities": vulnerabilities,
            "business_purpose": self._infer_purpose(endpoint),
            "critical_resource": risk_level == "alto",
            "tags": self._infer_tags(endpoint)
        }
    
    def _infer_tags(self, endpoint: Dict) -> List[str]:
        """Infere tags baseadas no path e método"""
        path = endpoint.get('path', '').lower()
        method = endpoint.get('method', '').upper()
        tags = []
        
        if 'user' in path or 'usuario' in path:
            tags.append("user-management")
        if 'auth' in path or 'login' in path:
            tags.append("authentication")
        if 'documento' in path:
            tags.append("document-management")
        if 'fluxo' in path:
            tags.append("workflow")
        if method in ['POST', 'PUT', 'PATCH']:
            tags.append("write-operation")
        if method == 'GET':
            tags.append("read-operation")
        if method == 'DELETE':
            tags.append("delete-operation")
        
        return tags
    
    def _infer_purpose(self, endpoint: Dict) -> str:
        """Infere propósito do endpoint baseado no path"""
        path = endpoint.get('path', '').lower()
        method = endpoint.get('method', '').upper()
        
        if 'user' in path or 'conta' in path:
            if method == 'GET':
                return "Consulta de usuários/contas"
            elif method == 'POST':
                return "Criação de usuários/contas"
            elif method == 'PUT':
                return "Atualização de usuários/contas"
            elif method == 'DELETE':
                return "Remoção de usuários/contas"
        
        if 'auth' in path or 'login' in path:
            return "Autenticação de usuários"
        
        if 'documento' in path:
            return "Gerenciamento de documentos"
        
        if 'fluxo' in path:
            return "Gerenciamento de fluxos de trabalho"
        
        if 'swagger' in path:
            return "Documentação da API"
        
        if 'metrics' in path:
            return "Métricas da API"
        
        return f"Operação {method} no recurso {path}"
    
    def analyze_endpoint(self, endpoint: Dict, code_context: str = "", max_retries: int = 2) -> Dict:
        """
        Analisa um endpoint com LLM, com fallback para heurística
        
        Args:
            endpoint: Dicionário com informações do endpoint
            code_context: Contexto do código ao redor do endpoint
            max_retries: Número máximo de tentativas
        """
        # Tenta análise com LLM
        for attempt in range(max_retries):
            try:
                result = self._call_llm(endpoint, code_context)
                if result and 'error' not in result:
                    # Valida se tem campos obrigatórios
                    required_fields = ['pii_fields', 'auth_required', 'risk_level']
                    if all(field in result for field in required_fields):
                        # Adiciona campos calculados
                        if 'risk_score' not in result:
                            result['risk_score'] = 0.9 if result.get('risk_level') == 'alto' else (0.5 if result.get('risk_level') == 'médio' else 0.1)
                        if 'tags' not in result:
                            result['tags'] = self._infer_tags(endpoint)
                        return result
                    else:
                        # Completa campos faltantes com heurística
                        heuristic = self._simple_heuristic_analysis(endpoint)
                        for field in required_fields:
                            if field not in result:
                                result[field] = heuristic[field]
                        if 'risk_score' not in result:
                            result['risk_score'] = heuristic.get('risk_score', 0.1)
                        if 'tags' not in result:
                            result['tags'] = heuristic.get('tags', [])
                        return result
                else:
                    # Print detalhado do erro retornado pelo LLM
                    error_msg = result.get('error', str(result)) if result else "Unknown error"
                    if "model" in error_msg and "not found" in error_msg:
                        print(f"   ⚠️  Modelo '{self.model}' não encontrado no {self.backend}")
                        print(f"   💡 Dica: Verifique se o modelo está instalado com 'ollama pull {self.model}'")
                        # Não tenta novamente se o modelo não existe
                        break
                    else:
                        print(f"   ⚠️  Erro LLM (tentativa {attempt + 1}): {error_msg[:100]}")
            except Exception as e:
                print(f"   ⚠️  Tentativa {attempt + 1} falhou: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
        # Fallback para análise heurística
        print("   ⚠️  Usando análise heurística (fallback)")
        return self._simple_heuristic_analysis(endpoint)
    
    def _call_llm(self, endpoint: Dict, code_context: str = "") -> Dict:
        """Chama o backend LLM (ai-gatiator ou Ollama) e processa a resposta"""
        prompt = f"""Responda apenas com JSON válido. Todas as chaves e strings DEVEM estar entre aspas duplas. Não inclua nenhum texto extra, comentários ou explicações.\n\nEndpoint: {endpoint.get('method', '')} {endpoint.get('path', '')}\nHandler: {endpoint.get('name', 'anonymous')}\n\nResponda EXATAMENTE neste formato:\n{{\"pii_fields\":[],\"auth_required\":false,\"auth_type\":\"jwt\",\"risk_level\":\"baixo\",\"risk_reason\":\"\",\"vulnerabilities\":[],\"business_purpose\":\"\",\"critical_resource\":false}}\n\nRegras rápidas:\n- pii_fields: adicione \"cpf\",\"email\",\"nome\",\"telefone\" se aparecerem no path\n- auth_required: true se endpoint requer login\n- risk_level: \"alto\" se tem PII, \"médio\" se modifica dados, \"baixo\" se só leitura\n- vulnerabilities: lista de strings, ex: [\"bola\", \"injection\"]. Nunca inclua objetos ou dicionários, apenas nomes simples.\n- vulnerabilities: adicione \"bola\" se tem :id no path\n\nApenas o JSON, nada mais.\n"""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        headers = {"Content-Type": "application/json"}
        if self.backend == "gatiator":
            headers["Authorization"] = "Bearer qualquer"
        try:
            response = requests.post(
                self.llm_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            if self.backend == "gatiator":
                provider = response.headers.get('X-Gateway-Provider')
                if provider:
                    print(f"      ℹ️ Provedor LLM usado: {provider}")
            if response.status_code != 200:
                return {"error": f"Erro {self.backend}: {response.status_code} {response.text}"}
            data = response.json()
            # Espera resposta no formato OpenAI: {choices: [{message: {content: ...}}]}
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            output = content.strip()
            # Procura por JSON na resposta
            start = output.find('{')
            end = output.rfind('}') + 1
            if start != -1 and end > start:
                json_str = output[start:end]
                json_str = ''.join(char for char in json_str if ord(char) >= 32 or char == '\n')
                return json.loads(json_str)
            else:
                return {"error": "Resposta não contém JSON", "raw": output[:200]}
        except requests.Timeout:
            return {"error": f"Timeout na análise LLM ({self.backend})"}
        except json.JSONDecodeError as e:
            return {"error": f"Erro parsing JSON: {e}"}
        except Exception as e:
            return {"error": str(e)}
    
    def analyze_batch(self, endpoints: List[Dict], code_by_file: Dict = None, use_llm: bool = True) -> List[Dict]:
        """
        Analisa múltiplos endpoints
        
        Args:
            endpoints: Lista de endpoints
            code_by_file: Dicionário {file_path: code_content}
            use_llm: Se False, usa apenas heurística (mais rápido)
        """
        results = []
        total = len(endpoints)
        
        for i, endpoint in enumerate(endpoints, 1):
            print(f"📊 Analisando {i}/{total}: {endpoint.get('method', '')} {endpoint.get('path', '')}")
            
            if use_llm:
                code_context = ""
                if code_by_file and endpoint.get('file_path'):
                    file_path = endpoint['file_path']
                    if file_path in code_by_file:
                        lines = code_by_file[file_path].split('\n')
                        line_num = endpoint.get('line_number', 0)
                        start = max(0, line_num - 5)
                        end = min(len(lines), line_num + 5)
                        code_context = '\n'.join(lines[start:end])
                
                analysis = self.analyze_endpoint(endpoint, code_context)
            else:
                analysis = self._simple_heuristic_analysis(endpoint)
            
            # Mescla análise com endpoint original
            enriched = {**endpoint, **analysis}
            results.append(enriched)
            
            # Mostra resultado
            if 'error' not in analysis:
                pii_str = f"PII: {analysis.get('pii_fields', [])}" if analysis.get('pii_fields') else "Sem PII"
                print(f"   ✅ {pii_str} | Risco: {analysis.get('risk_level', '?')} (score: {analysis.get('risk_score', 0):.2f})")
            else:
                print(f"   ⚠️  Usando heurística (LLM falhou)")
                heuristic = self._simple_heuristic_analysis(endpoint)
                results[-1] = {**endpoint, **heuristic}
                print(f"   ✅ {heuristic.get('risk_level', '?')} risco | Auth: {heuristic.get('auth_required', False)}")
        
        return results


def analyze_project_endpoints(endpoints_file: Union[str, Path] = None, 
                             endpoints: List[Dict] = None, 
                             output_file: Union[str, Path] = None, 
                             model: str = "codellama:7b", 
                             use_llm: bool = True, 
                             backend: str = "gatiator", 
                             llm_url: str = None, 
                             risk_threshold: float = 0.7, 
                             logger=None) -> Dict[str, Any]:
    """
    Analisa todos os endpoints de um arquivo JSON ou lista de endpoints
    
    Args:
        endpoints_file: Caminho para o arquivo all_endpoints.json (opcional se endpoints fornecido)
        endpoints: Lista de endpoints diretamente (opcional)
        output_file: Caminho para salvar resultados JSON (opcional, padrão: src/application/pipeline/tests/enriched_endpoints.json)
        model: Modelo LLM a usar
        use_llm: Se False, usa apenas análise heurística
        backend: Backend LLM ("gatiator", "ollama", "none")
        llm_url: URL customizada do backend LLM
        risk_threshold: Limiar de risco (0.0-1.0) para classificar como 'alto risco'
        logger: Logger opcional
    """
    # Carrega endpoints se arquivo foi fornecido
    if endpoints_file:
        endpoints_path = Path(endpoints_file)
        if not endpoints_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {endpoints_file}")
        
        with open(endpoints_path, 'r', encoding='utf-8') as f:
            endpoints = json.load(f)
    elif not endpoints:
        raise ValueError("Either endpoints_file or endpoints must be provided")
    
    total_endpoints = len(endpoints)
    if logger:
        logger.info(f"📁 Carregados {total_endpoints} endpoints")
    else:
        print(f"📁 Carregados {total_endpoints} endpoints")
    
    if use_llm:
        if logger:
            logger.info(f"🤖 Modo: LLM ({backend}) - Modelo: {model}")
        else:
            print(f"🤖 Modo: LLM ({backend}) - Modelo: {model}")
        if llm_url:
            if logger:
                logger.info(f"🔗 URL customizada: {llm_url}")
    else:
        if logger:
            logger.info("🤖 Modo: Heurística")
        else:
            print("🤖 Modo: Heurística")
    
    # Inicializa analisador
    from time import perf_counter
    start_time = perf_counter()
    analyzer = LocalLLMAnalyzer(model=model, backend=backend, llm_url=llm_url)
    
    # Analisa endpoints
    enriched_endpoints = analyzer.analyze_batch(endpoints, use_llm=use_llm)
    
    elapsed_time = perf_counter() - start_time
    print(f"\n⏱️ Tempo de análise: {elapsed_time:.2f} segundos")
    
    # Define diretórios fixos de saída conforme solicitado
    tests_dir = Path("src/application/pipeline/tests")
    output_dir = Path("output")
    
    # Garante que os diretórios existam
    tests_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Arquivo JSON sempre em src/application/pipeline/tests/
    json_output_file = tests_dir / "enriched_endpoints.json"
    
    # Salva resultados JSON
    with open(json_output_file, 'w', encoding='utf-8') as f:
        json.dump(enriched_endpoints, f, indent=2, ensure_ascii=False)
    
    # Gera estatísticas
    high_risk = sum(1 for e in enriched_endpoints if e.get('risk_level') == 'alto')
    medium_risk = sum(1 for e in enriched_endpoints if e.get('risk_level') == 'médio')
    low_risk = sum(1 for e in enriched_endpoints if e.get('risk_level') == 'baixo')
    errors = sum(1 for e in enriched_endpoints if 'error' in e)
    
    # Arquivo MD sempre em output/
    report_file = output_dir / "enriched_endpoints_report.md"
    generate_llm_report(enriched_endpoints, report_file)
    
    # Prepara resultado
    result = {
        "summary": {
            "total": total_endpoints,
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "low_risk": low_risk,
            "errors": errors,
            "use_llm": use_llm,
            "llm_calls": total_endpoints if use_llm else 0,
            "analysis_time_seconds": elapsed_time
        },
        "endpoints": enriched_endpoints,
        "high_risk_endpoints": [e for e in enriched_endpoints if e.get('risk_level') == 'alto']
    }
    
    if logger:
        logger.info(f"💾 Resultados JSON salvos em: {json_output_file}")
        logger.info(f"📊 Relatório MD salvo em: {report_file}")
    else:
        print(f"💾 Resultados JSON salvos em: {json_output_file}")
        print(f"📊 Relatório MD salvo em: {report_file}")
    
    return result


def generate_llm_report(endpoints: List[Dict], output_file: Path):
    """Gera relatório Markdown com análise"""
    
    # Estatísticas
    total = len(endpoints)
    if total == 0:
        print("⚠️ Nenhum endpoint para gerar relatório")
        return
    
    auth_required = sum(1 for e in endpoints if e.get('auth_required') == True)
    high_risk = sum(1 for e in endpoints if e.get('risk_level') == 'alto')
    medium_risk = sum(1 for e in endpoints if e.get('risk_level') == 'médio')
    low_risk = sum(1 for e in endpoints if e.get('risk_level') == 'baixo')
    has_pii = sum(1 for e in endpoints if e.get('pii_fields'))
    
    # Vulnerabilidades encontradas
    vuln_count = {}
    for e in endpoints:
        for v in e.get('vulnerabilities', []):
            if isinstance(v, dict):
                v = str(v)
            elif not isinstance(v, str):
                v = repr(v)
            vuln_count[v] = vuln_count.get(v, 0) + 1
    
    report = f"""# Relatório de Análise de Segurança de API

## 📊 Resumo

| Métrica | Valor |
|---------|-------|
| **Total de endpoints analisados** | {total} |
| **Endpoints com autenticação** | {auth_required} ({auth_required/total*100:.1f}%) |
| **Endpoints de alto risco** | {high_risk} ({high_risk/total*100:.1f}%) |
| **Endpoints de médio risco** | {medium_risk} ({medium_risk/total*100:.1f}%) |
| **Endpoints de baixo risco** | {low_risk} ({low_risk/total*100:.1f}%) |
| **Endpoints com dados PII** | {has_pii} ({has_pii/total*100:.1f}%) |

## 🚨 Vulnerabilidades Detectadas

| Vulnerabilidade | Quantidade | Severidade |
|----------------|------------|------------|
"""
    vuln_names = {
        "bola": "BOLA - Broken Object Level Authorization",
        "broken_auth": "Broken Authentication",
        "injection": "Injection (SQL/NoSQL/Command)",
        "bfla": "BFLA - Broken Function Level Authorization"
    }
    
    for vuln, count in sorted(vuln_count.items(), key=lambda x: x[1], reverse=True):
        name = vuln_names.get(vuln, vuln)
        severity = "🔴 Alta" if vuln in ["bola", "broken_auth"] else "🟡 Média"
        report += f"| {name} | {count} | {severity} |\n"
    
    if not vuln_count:
        report += "| Nenhuma vulnerabilidade detectada | 0 | - |\n"
    
    report += f"""
## 🔴 Endpoints de Alto Risco

| Método | Path | PII | Razão |
|--------|------|-----|-------|
"""
    for e in endpoints:
        if e.get('risk_level') == 'alto':
            pii = ', '.join(e.get('pii_fields', [])) if e.get('pii_fields') else '-'
            reason = (e.get('risk_reason') or 'Dados sensíveis')
            reason = str(reason)[:50]
            report += f"| {e.get('method', '')} | `{e.get('path', '')}` | {pii} | {reason} |\n"
    
    report += f"""
## 🟡 Endpoints de Médio Risco

| Método | Path | Vulnerabilidades |
|--------|------|------------------|
"""
    for e in endpoints:
        if e.get('risk_level') == 'médio':
            vulns = ', '.join(e.get('vulnerabilities', [])) if e.get('vulnerabilities') else '-'
            report += f"| {e.get('method', '')} | `{e.get('path', '')}` | {vulns} |\n"
    
    if medium_risk == 0:
        report += "| Nenhum endpoint de médio risco | - | - |\n"

    report += f"""
## 🔒 Endpoints com Dados PII

| Método | Path | Campos PII |
|--------|------|------------|
"""
    for e in endpoints:
        if e.get('pii_fields'):
            fields = ', '.join(e['pii_fields'])
            report += f"| {e.get('method', '')} | `{e.get('path', '')}` | {fields} |\n"
    
    if has_pii == 0:
        report += "| Nenhum endpoint com PII detectado | - | - |\n"
    
    from datetime import datetime
    datahora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    report += f"""
## 📋 Recomendações Prioritárias

1. **Revisar todos os endpoints de alto risco** ({high_risk} endpoints)
2. **Implementar validação de autorização** para endpoints com `:id` no path
3. **Proteger dados PII** em {has_pii} endpoints

---
*Relatório gerado automaticamente por análise estática de código em {datahora}*
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"📊 Relatório salvo em: {output_file}")


def find_latest_scan_endpoints(base_dir: str = "output") -> str | None:
    """Procura o all_endpoints.json do scan mais recente"""
    import glob
    
    if not os.path.isdir(base_dir):
        return None
    
    scan_dirs = glob.glob(os.path.join(base_dir, "scan_*"))
    if not scan_dirs:
        return None
    
    scan_dirs.sort(key=lambda x: os.path.basename(x), reverse=True)
    
    for scan_dir in scan_dirs:
        endpoints_file = os.path.join(scan_dir, "all_endpoints.json")
        if os.path.isfile(endpoints_file):
            return endpoints_file
    
    return None


def main():
    import sys
    import argparse
    import logging
    from pathlib import Path
    from datetime import datetime
    
    # Setup básico de logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("llm_analyzer.log", encoding="utf-8", mode="a")
        ]
    )
    logger = logging.getLogger(__name__)
    
    # Parse de argumentos
    parser = argparse.ArgumentParser(
        description="Analisador de risco e enriquecimento de endpoints via LLM/heurística",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "endpoints_file",
        nargs="?",
        default=None,
        help="Caminho para all_endpoints.json (opcional: busca automático em output/scan_*/)"
    )
    parser.add_argument(
        "--llm-backend",
        choices=["gatiator", "ollama", "none"],
        default=os.getenv("LLM_BACKEND", "none").lower(),
        help="Backend LLM: 'gatiator' (porta 1313), 'ollama' (porta 11434) ou 'none' para heurística pura"
    )
    parser.add_argument(
        "--llm-model",
        default=os.getenv("LLM_MODEL", "codellama:7b"),
        help="Modelo LLM a usar. Ex: codellama:7b, llama2, phi, etc."
    )
    parser.add_argument(
        "--llm-url",
        default=None,
        help="URL customizada do backend LLM (sobrepõe padrões)"
    )
    parser.add_argument(
        "--risk-threshold",
        type=float,
        default=0.7,
        help="Limiar de risco (0.0-1.0) para classificar como 'alto risco'"
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Desabilita LLM e usa apenas heurística"
    )
    
    args = parser.parse_args()
    
    # Resolução do arquivo de endpoints
    if args.endpoints_file:
        endpoints_file = Path(args.endpoints_file).resolve()
        if not endpoints_file.is_file():
            logger.error(f"❌ Arquivo não encontrado: {endpoints_file}")
            sys.exit(1)
        logger.info(f"📄 Usando arquivo explícito: {endpoints_file}")
        endpoints_path = str(endpoints_file)
    else:
        found = find_latest_scan_endpoints()
        if not found:
            logger.error("❌ Erro: Nenhum arquivo all_endpoints.json encontrado em output/scan_*/")
            logger.error("💡 Execute primeiro: python test_parser.py -i /caminho/do/projeto")
            sys.exit(1)
        endpoints_path = found
        logger.info(f"🔍 Scan mais recente detectado: {endpoints_path}")
    
    # Configuração do backend
    use_llm = not args.no_llm and args.llm_backend != "none"
    
    if use_llm:
        logger.info(f"🤖 LLM: {args.llm_backend} | Modelo: {args.llm_model}")
        if args.llm_url:
            logger.info(f"🔗 URL: {args.llm_url}")
    else:
        logger.info("🧠 Modo heurística pura (sem LLM)")
    
    # Execução da análise
    try:
        results = analyze_project_endpoints(
            endpoints_file=endpoints_path,
            model=args.llm_model,
            use_llm=use_llm,
            backend=args.llm_backend if use_llm else "none",
            llm_url=args.llm_url,
            risk_threshold=args.risk_threshold,
            logger=logger
        )
        
        # Resumo no console
        stats = results["summary"]
        print("\n" + "="*60)
        print("📈 RESUMO DA ANÁLISE DE RISCO")
        print("="*60)
        print(f"Total de endpoints analisados : {stats['total']}")
        print(f"Alto risco                    : {stats['high_risk']}")
        print(f"Médio risco                   : {stats['medium_risk']}")
        print(f"Baixo risco                   : {stats['low_risk']}")
        print(f"Erros na análise              : {stats['errors']}")
        if use_llm:
            print(f"LLM calls realizadas         : {stats['llm_calls']}")
        print(f"Tempo de análise              : {stats['analysis_time_seconds']:.2f}s")
        print("="*60)
        
        if results["high_risk_endpoints"]:
            print("\n⚠️  ENDPOINTS DE ALTO RISCO (revisão recomendada):")
            for ep in results["high_risk_endpoints"][:5]:
                score = ep.get('risk_score', 0)
                print(f"   • {ep.get('method', '')} {ep.get('path', '')} | Risco: {ep.get('risk_level', '?')} (score: {score:.2f})")
            if len(results["high_risk_endpoints"]) > 5:
                print(f"   ... e mais {len(results['high_risk_endpoints']) - 5}")
            
    except Exception as e:
        logger.exception(f"❌ Erro crítico durante a análise: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()