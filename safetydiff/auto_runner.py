"""SafetyDiff Auto-Runner: Delegates to ASRT when evaluation data is missing.

When a user requests a comparison for a model that has no data in the database,
SafetyDiff does NOT generate attacks itself. Instead, it:
1. Detects which model is missing.
2. Finds the reference prompts from the existing model's dataset.
3. Launches ASRT against the missing model using --resume for crash safety.
4. Waits for ASRT to finish.
5. Returns control to SafetyDiff to display the diff.

This keeps the separation of concerns clean:
  - ASRT = Attacker (generates, executes, judges)
  - SafetyDiff = Analyst (compares, diffs, reports)
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Optional


def get_available_models(db_path: str) -> list[str]:
    """Query the database for all models that have evaluation data."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT target_version FROM runs ORDER BY timestamp DESC")
    models = [row[0] for row in cursor.fetchall()]
    conn.close()
    return models


def get_model_result_count(db_path: str, model_name: str) -> int:
    """Return the number of evaluated results for a given model."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Check both target_version in runs and target_name in results
    cursor.execute(
        """SELECT COUNT(*) FROM results r
           JOIN runs rn ON r.run_id = rn.run_id
           WHERE rn.target_version = ?""",
        (model_name,),
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count


def detect_missing_model(
    db_path: str, old_model: str, new_model: str
) -> Optional[str]:
    """Check if either model is missing from the database. Returns the missing model name or None."""
    old_count = get_model_result_count(db_path, old_model)
    new_count = get_model_result_count(db_path, new_model)

    if old_count == 0 and new_count == 0:
        return f"BOTH:{old_model},{new_model}"
    if old_count == 0:
        return old_model
    if new_count == 0:
        return new_model
    return None


def infer_target_backend(model_name: str) -> tuple[str, str]:
    """Infer the ASRT --target backend and canonical model name from the user's input.
    
    Returns (target_type, model_name) tuple.
    """
    lower = model_name.lower()
    
    # OpenAI models
    if any(kw in lower for kw in ["gpt-", "gpt4", "o1-", "o3-", "chatgpt"]):
        return "openai", model_name
    
    # Anthropic models (via litellm)
    if any(kw in lower for kw in ["claude", "anthropic"]):
        return "litellm", model_name
    
    # Google models (via litellm)
    if any(kw in lower for kw in ["gemini", "palm"]):
        return "litellm", model_name
    
    # Default: assume Ollama (local model)
    return "ollama", model_name


def find_asrt_loop(safetydiff_root: Path) -> Optional[Path]:
    """Locate the ASRT loop.py script relative to the SafetyDiff installation."""
    # Try common relative paths
    candidates = [
        safetydiff_root.parent / "asrtloop" / "loop.py",        # f:\ASRT\asrtloop\loop.py
        safetydiff_root.parent.parent / "asrtloop" / "loop.py", # one level up
        Path(os.environ.get("ASRT_PATH", "")) / "loop.py",     # env var override
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def launch_asrt(
    model_name: str,
    asrt_path: Path,
    db_path: str,
    max_attacks: int = 860,
    interactive: bool = True,
) -> bool:
    """Launch ASRT to generate evaluation data for a missing model.
    
    Args:
        model_name: The model to evaluate (e.g., 'gpt-4o-mini', 'qwen2.5:7b')
        asrt_path: Path to ASRT's loop.py
        db_path: Path to the SQLite database
        max_attacks: Number of attacks to run
        interactive: If True, ask user for confirmation before launching
        
    Returns:
        True if ASRT completed successfully, False otherwise.
    """
    target_type, canonical_name = infer_target_backend(model_name)
    
    print(f"\n{'='*60}")
    print(f"  SafetyDiff Auto-Runner")
    print(f"{'='*60}")
    print(f"  Model '{model_name}' has no evaluation data in the database.")
    print(f"  Detected backend: {target_type}")
    print(f"  Attacks to run: {max_attacks}")
    print(f"{'='*60}")
    
    if interactive:
        response = input("\n  Launch ASRT to generate data? [Y/n]: ").strip().lower()
        if response in ("n", "no"):
            print("  Aborted. Cannot generate diff without data for both models.")
            return False
    
    # Build the ASRT command
    cmd = [
        sys.executable,
        str(asrt_path),
        "--target", target_type,
        "--model", canonical_name,
        "--attack-file", "hf",
        "--max-attacks", str(max_attacks),
        "--resume",  # Always use resume for crash safety
    ]
    
    print(f"\n  Running: {' '.join(cmd)}")
    print(f"  Working directory: {asrt_path.parent}")
    print()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(asrt_path.parent),
            check=False,
        )
        if result.returncode == 0:
            print(f"\n[+] ASRT completed successfully for '{model_name}'.")
            return True
        else:
            print(f"\n[!] ASRT exited with code {result.returncode}.")
            return False
    except KeyboardInterrupt:
        print("\n[!] ASRT interrupted by user.")
        return False
    except Exception as e:
        print(f"\n[!] Failed to launch ASRT: {e}")
        return False


def auto_run_if_needed(
    db_path: str,
    old_model: str,
    new_model: str,
    max_attacks: int = 860,
    interactive: bool = True,
) -> bool:
    """Check if data is missing for either model. If so, offer to launch ASRT.
    
    Returns True if both models now have data (either pre-existing or just generated).
    """
    missing = detect_missing_model(db_path, old_model, new_model)
    
    if missing is None:
        # Both models have data, proceed normally
        return True
    
    # Find ASRT
    safetydiff_root = Path(__file__).parent.parent
    asrt_path = find_asrt_loop(safetydiff_root)
    
    if asrt_path is None:
        print(f"\n[!] Cannot find ASRT (loop.py).")
        print(f"    Set the ASRT_PATH environment variable to the directory containing loop.py.")
        print(f"    Example: set ASRT_PATH=F:\\ASRT\\asrtloop")
        return False
    
    if missing.startswith("BOTH:"):
        models = missing.replace("BOTH:", "").split(",")
        print(f"\n[!] Neither '{models[0]}' nor '{models[1]}' has evaluation data.")
        print(f"    ASRT will need to run for BOTH models.")
        
        for model in models:
            success = launch_asrt(model, asrt_path, db_path, max_attacks, interactive)
            if not success:
                return False
        return True
    else:
        return launch_asrt(missing, asrt_path, db_path, max_attacks, interactive)
