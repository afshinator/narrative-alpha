import { useEffect, useState } from "react";

type FontSize = "sm" | "md" | "lg";

const SIZES: { key: FontSize; label: string; title: string }[] = [
  { key: "sm", label: "A−", title: "Small" },
  { key: "md", label: "A", title: "Medium" },
  { key: "lg", label: "A+", title: "Large" },
];

export function FontSizeControl() {
  const [size, setSize] = useState<FontSize>("md");

  useEffect(() => {
    document.documentElement.setAttribute("data-font-size", size);
  }, [size]);

  return (
    <div className="font-size-control">
      {SIZES.map(({ key, label, title }) => (
        <button
          key={key}
          className={`fs-btn${size === key ? " active" : ""}`}
          title={title}
          onClick={() => setSize(key)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
