"""Valida que os casos de uso apenas delegam às portas injetadas (mocks)."""

from gtsa.application.use_cases import (
    AnalyzeAndEnrichUseCase,
    BuildReportUseCase,
    GenerateExampleDataUseCase,
    RunSchemathesisUseCase,
)


class _FakeAnalyzer:
    def __init__(self):
        self.called_with = None

    def analyze(self, endpoints, openapi=None):
        self.called_with = (endpoints, openapi)
        return [{"path": "/x", "risk_level": "high"}]


class _FakeRunner:
    def run(self, only_high_risk=False, verbose=False):
        self.args = (only_high_risk, verbose)
        return 0


class _FakeExamples:
    def generate(self, openapi, only_with_body=True):
        return 3


class _FakeReport:
    def build(self, full=False, hide_success=False, hide_skip=False):
        return "report.md"


def test_analyze_use_case_delega():
    fake = _FakeAnalyzer()
    uc = AnalyzeAndEnrichUseCase(fake)
    out = uc.execute([{"path": "/x"}], openapi="openapi.json")
    assert fake.called_with == ([{"path": "/x"}], "openapi.json")
    assert out[0]["risk_level"] == "high"


def test_run_schemathesis_use_case_delega():
    fake = _FakeRunner()
    uc = RunSchemathesisUseCase(fake)
    assert uc.execute(only_high_risk=True, verbose=True) == 0
    assert fake.args == (True, True)


def test_examples_use_case_retorna_contagem():
    uc = GenerateExampleDataUseCase(_FakeExamples())
    assert uc.execute({"paths": {}}, only_with_body=True) == 3


def test_build_report_use_case_delega():
    uc = BuildReportUseCase(_FakeReport())
    assert uc.execute() == "report.md"
