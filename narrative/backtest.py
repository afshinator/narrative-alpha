"""Background back-test worker for outlet reputation scoring.

Invoked via modal.Function.spawn() — non-blocking, fire-and-forget.
Runs after main pipeline returns. Analyzes historical articles from
a single domain to populate scatter_shot_anomaly_factor and
historical_origin_validation_rate.
"""


def execute_historical_backtest(domain: str, vertical: str) -> None:
    """
    Background task: back-test an outlet's historical accuracy.

    Historical backtesting does not attempt to reconstruct 30-day absorption
    behavior (that belongs to the online outlier_tracking system). Instead, it
    approximates outlet reliability through cross-source persistence.

    1. SERP Query 1 (target): site:{domain} {vertical}, tbm=nws, num=15, tbs=qdr:y
    2. SERP Query 2 (baseline): {vertical}, tbm=nws, num=15, tbs=qdr:y — no site filter
    3. Web Unlocker: fetch article bodies from both queries
    4. Floor gate: if either query < 5 articles → UNRATED, exit
    5. Call 1 + Call 3 on both article sets independently
    6. Classify claims from target against consensus baseline:
       - consensus-supported: claim appears in multi-source consensus
       - consensus-isolated: claim appears only in target outlet's graph
    7. Compute metrics:
       historical_origin_validation_rate = consensus_supported / total_claims
       scatter_shot_anomaly_factor       = consensus_isolated / total_claims
    8. Write Sa, historical_origin_validation_rate, rating_status='RATED' to SQLite

    Naming discipline: consensus-supported/consensus-isolated are distinct from
    the Section 5 absorbed/decayed lifecycle, which is exclusive to real-time
    outlier_tracking. The output metrics have the same names and ranges — only
    the data source and time window differ.

    Args:
        domain: source domain to back-test (e.g. "globalwire.com")
        vertical: industry vertical (e.g. "TECHNOLOGY")
    """
    pass
