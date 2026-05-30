interface BadgeProps {
  level: string;
  label: string;
}

export function Badge({ level, label }: BadgeProps) {
  const className = level === "HIGH" ? "badge badge-high"
    : level === "MED" ? "badge badge-med"
    : "badge badge-low";
  return <span className={className}>{label}</span>;
}
