from gtsa.domain.value_objects import HttpMethod, RiskLevel, Role


def test_http_method_parse_normaliza_case():
    assert HttpMethod.parse("post") is HttpMethod.POST
    assert HttpMethod.parse(" GET ") is HttpMethod.GET


def test_risk_level_is_high_or_above():
    assert RiskLevel.HIGH.is_high_or_above
    assert RiskLevel.CRITICAL.is_high_or_above
    assert not RiskLevel.LOW.is_high_or_above


def test_role_values_sao_strings():
    assert isinstance(Role.REQUISITANTE.value, str)
