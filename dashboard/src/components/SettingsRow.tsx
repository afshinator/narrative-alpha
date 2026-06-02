const PROVIDERS = ["deepseek", "openai", "google", "groq"] as const;

interface SettingsRowProps {
  slotName: string;
  slotDescription: string;
  provider: string;
  model: string;
  onChange: (model: string) => void;
  onProviderChange: (provider: string) => void;
}

export function SettingsRow({
  slotName,
  slotDescription,
  provider,
  model,
  onChange,
  onProviderChange,
}: SettingsRowProps) {
  return (
    <div className="settings-row">
      <div className="settings-slot">
        {slotName}
        <div className="settings-slot-sub">{slotDescription}</div>
      </div>
      <select
        value={provider}
        onChange={(e) => onProviderChange(e.target.value)}
        aria-label={`Provider for ${slotName}`}
      >
        {PROVIDERS.map((p) => (
          <option key={p} value={p}>{p}</option>
        ))}
      </select>
      <input
        type="text"
        value={model}
        onChange={(e) => onChange(e.target.value)}
        aria-label={`Model for ${slotName}`}
      />
    </div>
  );
}
