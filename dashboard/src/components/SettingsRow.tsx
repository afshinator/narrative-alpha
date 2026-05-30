interface SettingsRowProps {
  slotName: string;
  slotDescription: string;
  model: string;
  onChange: (model: string) => void;
}

export function SettingsRow({ slotName, slotDescription, model, onChange }: SettingsRowProps) {
  return (
    <div className="settings-row">
      <div className="settings-slot">
        {slotName}
        <div className="settings-slot-sub">{slotDescription}</div>
      </div>
      <input
        type="text"
        value={model}
        onChange={(e) => onChange(e.target.value)}
        aria-label={`Model for ${slotName}`}
      />
    </div>
  );
}
