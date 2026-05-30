import { useState } from "react";
import type { LLMConfig, LLMSlotConfig } from "../types";
import { SettingsRow } from "./SettingsRow";

const DEFAULT_CONFIG: LLMConfig = {
  call_1_entity_normalization: { provider: "deepseek", model: "deepseek-v4-flash", thinking: false, temperature: 0.1 },
  call_2_linguistic_neutralization: { provider: "deepseek", model: "deepseek-v4-flash", thinking: false, temperature: 0.2 },
  call_3_graph_extraction: { provider: "deepseek", model: "deepseek-v4-flash", thinking: true, temperature: 0.3 },
  call_4_forensic_synthesis: { provider: "deepseek", model: "deepseek-v4-flash", thinking: true, temperature: 0.4 },
};

const SLOTS: { key: keyof LLMConfig; name: string; description: string }[] = [
  { key: "call_1_entity_normalization", name: "Call 1", description: "Entity normalization" },
  { key: "call_2_linguistic_neutralization", name: "Call 2", description: "Linguistic neutralization" },
  { key: "call_3_graph_extraction", name: "Call 3", description: "Graph extraction" },
  { key: "call_4_forensic_synthesis", name: "Call 4", description: "Forensic synthesis" },
];

export function SettingsPage() {
  const [config, setConfig] = useState<LLMConfig>(DEFAULT_CONFIG);

  const handleUpdate = (key: keyof LLMConfig, updates: Partial<LLMSlotConfig>) => {
    setConfig((prev) => ({
      ...prev,
      [key]: { ...prev[key], ...updates },
    }));
  };

  const handleSave = () => {
    localStorage.setItem("llmConfig", JSON.stringify(config));
  };

  return (
    <div className="page settings-page">
      <h2 className="section-title">LLM Configuration</h2>
      <p className="section-subtitle">
        Configure per-slot LLM providers and parameters for the forensic pipeline.
      </p>

      <div className="settings-table">
        <div className="settings-header">
          <div>Call Slot</div>
          <div>Provider</div>
          <div>Model</div>
          <div>Temperature</div>
          <div>Thinking</div>
        </div>

        {SLOTS.map(({ key, name, description }) => (
          <SettingsRow
            key={key}
            slotName={name}
            slotDescription={description}
            provider={config[key].provider}
            model={config[key].model}
            thinking={config[key].thinking}
            temperature={config[key].temperature}
            onUpdate={(updates) => handleUpdate(key, updates)}
          />
        ))}
      </div>

      <button className="btn-save" onClick={handleSave}>
        Save Configuration
      </button>
    </div>
  );
}
