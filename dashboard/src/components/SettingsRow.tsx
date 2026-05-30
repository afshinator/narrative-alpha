interface SettingsRowProps {
  slotName: string;
  slotDescription: string;
  provider: string;
  model: string;
  thinking: boolean;
  temperature: number;
  onUpdate: (updates: Partial<{ provider: string; model: string; thinking: boolean; temperature: number }>) => void;
}

const PROVIDERS = ["deepseek", "openai", "google", "groq"];

export function SettingsRow({
  slotName,
  slotDescription,
  provider,
  model,
  thinking,
  temperature,
  onUpdate,
}: SettingsRowProps) {
  return (
    <div className="settings-row">
      <div className="settings-slot">
        {slotName}
        <div className="settings-slot-sub">{slotDescription}</div>
      </div>

      <select
        value={provider}
        onChange={(e) => onUpdate({ provider: e.target.value })}
      >
        {PROVIDERS.map((p) => (
          <option key={p} value={p}>{p}</option>
        ))}
      </select>

      <input
        type="text"
        value={model}
        onChange={(e) => onUpdate({ model: e.target.value })}
      />

      <input
        type="range"
        min="0"
        max="2"
        step="0.1"
        value={temperature}
        onChange={(e) => onUpdate({ temperature: parseFloat(e.target.value) })}
        title={`Temperature: ${temperature}`}
      />

      {provider === "deepseek" ? (
        <div className="thinking-toggle">
          <input
            type="checkbox"
            checked={thinking}
            onChange={(e) => onUpdate({ thinking: e.target.checked })}
          />
          <span>{thinking ? "On" : "Off"}</span>
        </div>
      ) : (
        <div className="thinking-toggle">
          <span style={{ color: "var(--text-tertiary)", fontSize: 10 }}>N/A</span>
        </div>
      )}
    </div>
  );
}
