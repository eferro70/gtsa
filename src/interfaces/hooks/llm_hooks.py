import schemathesis
from .auth_hooks import apply_auth

@schemathesis.hook
def before_call(context, case, **kwargs):
    if case.headers is None:
        case.headers = {}

    # Força o Content-Type para evitar erros 422/415
    case.headers["Content-Type"] = "application/json"
    case.headers["Accept"] = "application/json"

    # Aplica autenticação e chave de sistema
    apply_auth(case)