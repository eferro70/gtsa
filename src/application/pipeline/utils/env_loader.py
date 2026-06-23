#!/usr/bin/env python3
"""
utils/env_loader.py
-------------------
Utilitário para carregar arquivos .env com suporte a parâmetro --env-file
"""

import os
import sys
from pathlib import Path
from typing import Optional

def load_environment(env_file: Optional[str] = None, verbose: bool = False):
    """
    Carrega arquivos .env em ordem de prioridade.
    
    Args:
        env_file: Nome do arquivo .env (ex: ".env.serproid")
        verbose: Se True, exibe logs de carregamento
    """
    try:
        from dotenv import load_dotenv
        
        # Lista de arquivos a tentar carregar
        env_files = []
        
        # 1. Arquivo especificado pelo usuário (prioridade máxima)
        if env_file:
            env_path = Path(env_file)
            if env_path.exists():
                env_files.append(env_path)
            elif verbose:
                print(f"⚠️  Arquivo .env especificado não encontrado: {env_file}")
        
        # 2. Arquivos de fallback genéricos (sem nomes de projeto hardcoded)
        #    Carregados SEM override — apenas preenchem variáveis ainda não definidas.
        project_root = Path(__file__).parent.parent.parent
        default_envs = [
            project_root / ".env",
            Path(".env"),
        ]
        for env in default_envs:
            if env.exists() and env not in env_files:
                if verbose:
                    print(f"📄 Fallback .env encontrado: {env}")
                load_dotenv(env, override=False)

        # 3. Carrega o arquivo especificado pelo usuário por último, com override=True
        #    Garante que suas variáveis têm prioridade máxima sobre qualquer fallback.
        loaded = False
        for env_path in env_files:
            load_dotenv(env_path, override=True)
            if verbose:
                print(f"✅ Carregado (override): {env_path}")
            loaded = True

        if not loaded:
            load_dotenv()
            if verbose:
                print("⚠️  Nenhum arquivo .env específico encontrado. Usando load_dotenv() padrão.")
        
        # 4. Carrega .env.local se existir (sobrescreve)
        local_env = project_root / ".env.local"
        if local_env.exists():
            load_dotenv(local_env, override=True)
            if verbose:
                print(f"✅ Sobrescrito por: {local_env}")
        
    except ImportError:
        if verbose:
            print("⚠️  python-dotenv não instalado. Variáveis do .env não serão carregadas.")
            print("   Instale com: pip install python-dotenv")

def add_env_arg(parser):
    """Adiciona o argumento --env-file a um parser argparse"""
    parser.add_argument(
        '--env-file',
        help='Caminho para o arquivo .env (ex: .env.serproid)',
        default=None
    )
    return parser

def get_env_file_from_args(args):
    """Extrai o nome do arquivo .env dos argumentos"""
    return getattr(args, 'env_file', None)