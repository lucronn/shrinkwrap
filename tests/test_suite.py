from shrinkwrap.shell.guidance import analyze_shell_command
from shrinkwrap.gap_report.gap_report import generate_gap_report
from shrinkwrap.benchmarks.runner import run_benchmark_suite

def test_shell_guidance():
    res = analyze_shell_command("git status")
    assert "action" in res

def test_gap_report():
    report = generate_gap_report()
    assert "Codex Host Interception Gap Report" in report

def test_benchmarks():
    res = run_benchmark_suite()
    assert res["summary"]["total_cases"] == 9
    assert res["summary"]["overall_token_savings_pct"] > 80.0
