import { useState, useEffect } from "react";
import type { LLMConfig, LLMSlotConfig } from "../types";
import { SettingsRow } from "./SettingsRow";
import { EnvHealthPanel } from "./EnvHealthPanel";
import { fetchConfig, saveConfig } from "../api";

const SLOTS: { key: keyof LLMConfig; name: string; description: string }[] = [
  { key: "call_1_entity_normalization", name: "Call 1", description: "Entity normalization" },
  { key: "call_2_linguistic_neutralization", name: "Call 2", description: "Linguistic neutralization" },
  { key: "call_3_graph_extraction", name: "Call 3", description: "Graph extraction" },
  { key: "call_4_forensic_synthesis", name: "Call 4", description: "Forensic synthesis" },
];

export function SettingsPage() {
  const [config, setConfig] = useState<LLMConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  useEffect(() => {
    fetchConfig()
      .then(setConfig)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleUpdate = (key: keyof LLMConfig, updates: Partial<LLMSlotConfig>) => {
    setConfig((prev) => {
      if (!prev) return prev;
      return { ...prev, [key]: { ...prev[key], ...updates } };
    });
  };

  const handleSave = async () => {
    if (!config) return;
    setSaveStatus("Saving…");
    try {
      const result = await saveConfig(config);
      setSaveStatus(result.status === "ok" ? "Saved" : `Error: ${result.status}`);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setSaveStatus(`Save failed: ${msg}`);
    }
  };

  if (loading) return <div className="page settings-page"><p className="loading">Loading config…</p></div>;
  if (error) return <div className="page settings-page"><p className="error">Error: {error}</p></div>;
  if (!config) return <div className="page settings-page"><p className="empty">No configuration loaded.</p></div>;

  return (
    <div className="page settings-page">
      <h2 className="section-title">LLM Configuration</h2>
      <p className="section-subtitle">
        Configure the model name for each pipeline call slot. Other parameters are managed via server config.
      </p>

      <EnvHealthPanel />

      <div className="settings-table">
        <div className="settings-header">
          <div>Call Slot</div>
          <div>Model</div>
        </div>

        {SLOTS.map(({ key, name, description }) => (
          <SettingsRow
            key={key}
            slotName={name}
            slotDescription={description}
            model={config[key].model}
            onChange={(model) => handleUpdate(key, { model })}
          />
        ))}
      </div>

      <div className="settings-actions">
        <button className="btn-save" onClick={handleSave}>Save Configuration</button>
        {saveStatus && <span className="save-status">{saveStatus}</span>}
      </div>
    </div>
  );
}
