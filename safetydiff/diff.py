from .schema import RunReport, DiffReport, DiffResult

def compare_runs(old_run: RunReport, new_run: RunReport) -> DiffReport:
    """Compares two ASRT runs and generates a regression report."""
    
    # We only compare attacks that exist in both runs to ensure fairness.
    common_ids = set(old_run.results.keys()).intersection(set(new_run.results.keys()))
    
    newly_broken = []
    newly_fixed = []
    stable_failures = []
    stable_safe = []
    
    old_successes = 0
    new_successes = 0
    total = len(common_ids)

    for attack_id in common_ids:
        old_res = old_run.results[attack_id]
        new_res = new_run.results[attack_id]
        
        old_unsafe = old_res.is_unsafe
        new_unsafe = new_res.is_unsafe
        
        if old_unsafe:
            old_successes += 1
        if new_unsafe:
            new_successes += 1
            
        diff_res = DiffResult(
            attack_id=attack_id,
            category=new_res.category,
            old_verdict=old_res.verdict,
            new_verdict=new_res.verdict,
            old_score=old_res.score,
            new_score=new_res.score,
            status=""
        )
        
        if not old_unsafe and new_unsafe:
            diff_res.status = "newly_broken"
            newly_broken.append(diff_res)
        elif old_unsafe and not new_unsafe:
            diff_res.status = "newly_fixed"
            newly_fixed.append(diff_res)
        elif old_unsafe and new_unsafe:
            diff_res.status = "stable_failure"
            stable_failures.append(diff_res)
        else:
            diff_res.status = "stable_safe"
            stable_safe.append(diff_res)

    old_asr = (old_successes / total) if total else 0.0
    new_asr = (new_successes / total) if total else 0.0
    delta_asr = new_asr - old_asr
    
    return DiffReport(
        old_meta=old_run.meta,
        new_meta=new_run.meta,
        old_asr=old_asr,
        new_asr=new_asr,
        delta_asr=delta_asr,
        total_attacks=total,
        newly_broken=newly_broken,
        newly_fixed=newly_fixed,
        stable_failures=stable_failures,
        stable_safe=stable_safe,
    )
