import type { ChangeEvent, ReactNode } from "react";
import { useState } from "react";

export function Card({ title, actions, children }: { title?: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <section className="card">
      {(title || actions) && (
        <header className="card-head">
          {title && <h2>{title}</h2>}
          {actions && <div className="row gap">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

export function Button({
  children,
  onClick,
  variant = "solid",
  disabled,
  title,
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "solid" | "ghost";
  disabled?: boolean;
  title?: string;
}) {
  return (
    <button className={variant} onClick={onClick} disabled={disabled} title={title} type="button">
      {children}
    </button>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

export function Select({
  value,
  options,
  onChange,
}: {
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}) {
  return (
    <select value={value} onChange={(event: ChangeEvent<HTMLSelectElement>) => onChange(event.target.value)}>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

export function Slider({
  value,
  min,
  max,
  step,
  onChange,
}: {
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
}) {
  return (
    <div className="row gap">
      <input
        type="range"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      <output className="mono">{value.toFixed(2)}</output>
    </div>
  );
}

// Copy feedback is local state, so no parent needs to track it.
export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };
  return (
    <Button variant="ghost" onClick={copy} disabled={!text}>
      {copied ? "Copied" : label}
    </Button>
  );
}

export function Banner({ kind, children }: { kind: "error" | "info"; children: ReactNode }) {
  return <p className={`banner ${kind}`}>{children}</p>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="empty">{children}</p>;
}
