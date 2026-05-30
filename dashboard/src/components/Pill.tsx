import type { ReactNode } from "react";

interface PillProps {
  children: ReactNode;
}

export function Pill({ children }: PillProps) {
  return <span className="node-pill">{children}</span>;
}
