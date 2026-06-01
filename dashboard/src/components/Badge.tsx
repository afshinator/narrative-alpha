interface BadgeProps {
	level: string;
	label: string;
}

export function Badge({ level, label }: BadgeProps) {
	const className =
		level === "HIGH"
			? "badge badge-high"
			: level === "MED"
				? "badge badge-med"
				: "badge badge-low";
	const levelName =
		level === "HIGH" ? "High" : level === "MED" ? "Medium" : "Low";
	return (
		<span
			className={className}
			role="status"
			aria-label={`${levelName}: ${label}`}
		>
			{label}
		</span>
	);
}
