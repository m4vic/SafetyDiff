import json
from pathlib import Path
from typing import Union
from .schema import RunMetadata, AttackResult, RunReport

def load_run(file_path: Union[str, Path]) -> RunReport:
    """Loads an ASRT run JSON file and validates the structure into schema objects."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Run file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_meta = data.get("meta", {})
    meta = RunMetadata(
        run_id=raw_meta.get("run_id", "unknown"),
        suite_id=raw_meta.get("suite_id", "unknown"),
        target_id=raw_meta.get("target_id", "unknown"),
        target_version=raw_meta.get("target_version", "unknown"),
        timestamp=raw_meta.get("timestamp", "unknown"),
        improvement_enabled=raw_meta.get("improvement_enabled", False),
        generation_method=raw_meta.get("generation_method", "template"),
        target_config=raw_meta.get("target_config", {}),
        judge_id=raw_meta.get("judge_id", "none"),
        judge_version=raw_meta.get("judge_version", "none"),
    )

    summary = data.get("summary", {})
    raw_results = data.get("results", [])

    results_map = {}
    for res in raw_results:
        attack = AttackResult(
            attack_id=res.get("attack_id", "unknown"),
            category=res.get("category", "unknown"),
            intent=res.get("intent", "unknown"),
            verdict=res.get("verdict", "unknown"),
            score=float(res.get("score", 0.0)),
            severity=res.get("severity", "none"),
            policy_violated=res.get("policy_violated", "None"),
            reasoning=res.get("reasoning", ""),
            prompt=res.get("prompt", ""),
            response=res.get("response", ""),
        )
        results_map[attack.attack_id] = attack

    return RunReport(meta=meta, summary=summary, results=results_map)


def load_run_from_db(db_path: Union[str, Path], identifier: str) -> RunReport:
    """Loads a run from the SQLite database by run_id or target_name (most recent)."""
    import sqlite3
    
    db_file = Path(db_path)
    if not db_file.exists():
        raise FileNotFoundError(f"Database not found at: {db_file}")

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Try to find by run_id first
    cursor.execute("SELECT * FROM runs WHERE run_id = ?", (identifier,))
    run_row = cursor.fetchone()

    # 2. Try by target_version (model name) if not found
    if not run_row:
        cursor.execute(
            "SELECT * FROM runs WHERE target_version = ? ORDER BY timestamp DESC LIMIT 1",
            (identifier,)
        )
        run_row = cursor.fetchone()

    # 3. Try by target_id if still not found
    if not run_row:
        cursor.execute(
            "SELECT * FROM runs WHERE target_id = ? ORDER BY timestamp DESC LIMIT 1",
            (identifier,)
        )
        run_row = cursor.fetchone()

    if not run_row:
        conn.close()
        raise ValueError(f"Could not find run or target matching '{identifier}' in database.")

    run_id = run_row["run_id"]
    meta = RunMetadata(
        run_id=run_id,
        suite_id=run_row["suite_id"],
        target_id=run_row["target_id"],
        target_version=run_row["target_version"],
        timestamp=run_row["timestamp"],
        improvement_enabled=False,
        generation_method="unknown",
        target_config={},
        judge_id=run_row["judge_id"],
        judge_version=run_row["judge_version"],
    )

    # 4. Fetch results
    cursor.execute("SELECT * FROM results WHERE run_id = ?", (run_id,))
    results_rows = cursor.fetchall()

    results_map = {}
    for r in results_rows:
        attack = AttackResult(
            attack_id=r["attack_id"],
            category=r["category"],
            intent=r["intent"],
            verdict=r["verdict"],
            score=float(r["score"] or 0.0),
            severity=r["severity"],
            policy_violated=r["policy_violated"] or "None",
            reasoning=r["reasoning"] or "",
            prompt=r["prompt"] or "",
            response=r["response"] or "",
        )
        results_map[attack.attack_id] = attack

    conn.close()
    
    summary = {
        "attack_success_rate": run_row["attack_success_rate"],
        "total_attacks": run_row["total_attacks"],
    }
    
    return RunReport(meta=meta, summary=summary, results=results_map)
