import { useState, useEffect, useCallback } from "react";
import type { EnvHealth } from "../types";
import { fetchEnvHealth } from "../api";

export function EnvHealthPanel() {
  const [health, setHealth] = useState<EnvHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchEnvHealth()
      .then(setHealth)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="env-health-panel">
      <h3 className="env-health-title">Environment Variables</h3>
      {loading && <p className="loading">Checking environment…</p>}
      {error && <p className="error">Could not load env status: {error}</p>}
      {!loading && !error && health && (
        <>
          <ul className="env-var-list">
            {health.present.map((v) => (
              <li key={v} className="env-var env-var--present">
                <span className="env-var-indicator" aria-hidden="true">✓</span>
                <code>{v}</code>
              </li>
            ))}
            {health.missing.map((v) => (
              <li key={v} className="env-var env-var--missing">
                <span className="env-var-indicator" aria-hidden="true">✗</span>
                <code>{v}</code>
                <span className="env-var-hint">Not set — add to .env and restart server</span>
              </li>
            ))}
          </ul>
          {health.status === "ok" && (
            <p className="env-health-ok">All required variables are set.</p>
          )}
        </>
      )}
      <button className="btn-reload-env" onClick={load} disabled={loading}>
        {loading ? "Checking…" : "Recheck"}
      </button>
    </div>
  );
}
