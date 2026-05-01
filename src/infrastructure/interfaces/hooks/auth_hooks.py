import os
import json
from dotenv import load_dotenv
from pathlib import Path

# Busca auth_config.json subindo diretórios
def find_config(filename):
    path = Path.cwd()
    for _ in range(6):
        candidate = path / filename
        if candidate.exists():
            return candidate
        candidate_config = path / 'config' / filename
        if candidate_config.exists():
            return candidate_config
        if path.parent == path:
            break
        path = path.parent
    raise FileNotFoundError(f"Arquivo de configuração de autenticação não encontrado: {filename}")

config_path = find_config('auth_config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    AUTH_CONFIG = json.load(f)

# Busca .env
def find_env(filename):
    path = Path.cwd()
    for _ in range(6):
        candidate = path / filename
        if candidate.exists():
            return candidate
        if path.parent == path:
            break
        path = path.parent
    return None

env_path = find_env('.env')
if env_path:
    load_dotenv(dotenv_path=env_path)

def get_env_value(var):
    val = os.getenv(var)
    if val is None:
        print(f"[!] Variável de ambiente '{var}' não encontrada no .env")
    return val

def apply_auth(case, role=None):
    if case.headers is None:
        case.headers = {}

    # Headers fixos
    for header in AUTH_CONFIG.get("fixed_headers", []):
        header_name = header["name"]
        env_var = header.get("env_var")
        value = header.get("value")
        if env_var:
            env_val = get_env_value(env_var)
            if env_val:
                case.headers[header_name] = env_val
        elif value:
            case.headers[header_name] = value

    # Token baseado na role
    role_tokens = AUTH_CONFIG.get("role_tokens", {})
    target_role = role or AUTH_CONFIG.get("default_role")

    if target_role and target_role in role_tokens:
        token_env = role_tokens[target_role].get("env_var")
        token_value = role_tokens[target_role].get("value")
        token = get_env_value(token_env) if token_env else token_value
        if token:
            auth_header = AUTH_CONFIG.get("auth_header", "Authorization")
            prefix = AUTH_CONFIG.get("auth_prefix", "Bearer ")
            case.headers[auth_header] = f"{prefix}{token.strip()}"

    return case.headers.get(auth_header) is not None