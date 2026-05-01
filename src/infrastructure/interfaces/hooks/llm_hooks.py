import schemathesis
from .auth_hooks import apply_auth

@schemathesis.hook
def before_call(context, case, **kwargs):
    if case.headers is None:
        case.headers = {}

    # Força headers padrão
    case.headers["Content-Type"] = "application/json"
    case.headers["Accept"] = "application/json"

    # Extrai role do caso (se disponível)
    role = getattr(case, 'role', None)
    apply_auth(case, role=role)

    # Log de segurança (opcional)
    if hasattr(case, 'security_context'):
        vulns = case.security_context.get('vulnerabilities', [])
        if vulns:
            print(f"[SECURITY] Testando endpoint com vulnerabilidades conhecidas: {', '.join(vulns)}")