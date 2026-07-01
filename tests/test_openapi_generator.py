from gtsa.infrastructure.openapi.generator import OpenApiGeneratorAdapter


def test_gera_path_externo_e_security():
    gen = OpenApiGeneratorAdapter(prefix="/api/v1", base_url="http://x")
    endpoints = [
        {
            "method": "POST",
            "path": "/api/foo/:id",
            "handler": "createFoo",
            "parameters": [],
            "auth_required": True,
        }
    ]
    schema = gen.generate(endpoints)

    assert "/api/v1/foo/{id}" in schema["paths"]
    op = schema["paths"]["/api/v1/foo/{id}"]["post"]
    assert op["security"] == [{"bearerAuth": []}]
    # parâmetro de path deve ser inferido
    assert any(p["name"] == "id" and p["in"] == "path" for p in op["parameters"])
