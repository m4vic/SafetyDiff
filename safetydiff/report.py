import json
from pathlib import Path
from .schema import DiffReport

def generate_markdown(report: DiffReport) -> str:
    """Generates a human-readable markdown report from a DiffReport."""
    lines = []
    
    # Title & Metadata
    lines.append("# SafetyDiff Regression Report")
    lines.append("")
    lines.append(f"**Baseline Run:** `{report.old_meta.run_id}` (Model: `{report.old_meta.target_id}`)")
    lines.append(f"**New Run:** `{report.new_meta.run_id}` (Model: `{report.new_meta.target_id}`)")
    lines.append(f"**Attacks Compared:** {report.total_attacks}")
    lines.append("")
    
    # High Level Summary
    lines.append("## High-Level Metrics")
    lines.append(f"- **Baseline ASR:** {report.old_asr * 100:.1f}%")
    lines.append(f"- **New ASR:** {report.new_asr * 100:.1f}%")
    
    delta = report.delta_asr * 100
    if delta > 0:
        lines.append(f"- **Delta:** 🔴 +{delta:.1f}% (Regression: More attacks succeeding)")
    elif delta < 0:
        lines.append(f"- **Delta:** 🟢 {delta:.1f}% (Improvement: Fewer attacks succeeding)")
    else:
        lines.append(f"- **Delta:** ⚪ 0.0% (No change in overall ASR)")
    lines.append("")
    
    # Breakdown
    lines.append("## Breakdown")
    lines.append(f"- ⚠️ **Newly Broken:** {len(report.newly_broken)}")
    lines.append(f"- ✅ **Newly Fixed:** {len(report.newly_fixed)}")
    lines.append(f"- ❌ **Stable Failures:** {len(report.stable_failures)}")
    lines.append(f"- 🛡️ **Stable Safe:** {len(report.stable_safe)}")
    lines.append("")
    
    def _format_table(title: str, results: list):
        if not results:
            return ""
        table = []
        table.append(f"### {title}")
        table.append("| Attack ID | Category | Old Score | New Score |")
        table.append("|-----------|----------|-----------|-----------|")
        for res in results:
            table.append(f"| `{res.attack_id}` | {res.category} | {res.old_score} | {res.new_score} |")
        table.append("")
        return "\n".join(table)
    
    lines.append(_format_table("⚠️ Newly Broken (Regressions)", report.newly_broken))
    lines.append(_format_table("✅ Newly Fixed (Improvements)", report.newly_fixed))
    lines.append(_format_table("❌ Stable Failures (Unresolved)", report.stable_failures))
    
    return "\n".join(lines)


def export_report(report: DiffReport, out_path: str, format: str = "markdown"):
    """Exports the report to disk."""
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if format == "json":
        # Convert dataclasses to dict using a simple lambda or custom encoder
        import dataclasses
        class EnhancedJSONEncoder(json.JSONEncoder):
            def default(self, o):
                if dataclasses.is_dataclass(o):
                    return dataclasses.asdict(o)
                return super().default(o)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, cls=EnhancedJSONEncoder, indent=2)
            
    else:
        content = generate_markdown(report)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
