import React from "react";

type ConfigCardProps = {
  title: string;
  icon?: React.ReactNode;
  enabled: boolean;
  onToggle: (next: boolean) => void;
  accent?: string;
  children: React.ReactNode;
};

const ConfigCard = ({
  title,
  icon,
  enabled,
  onToggle,
  accent = "#3b82f6",
  children,
}: ConfigCardProps) => {
  return (
    <section
      className="rounded-2xl border-2 border-solid transition-colors"
      style={{
        ["--accent" as any]: accent,
        borderColor: enabled ? accent : "#cbd5e1",
        backgroundColor: enabled
          ? "color-mix(in srgb, var(--accent) 20%, white)"
          : "white",
      }}
      aria-label={title}
    >
        <header>
            <div className="flex flex-row justify-between p-2">
                {icon}
                <span>{title}</span>
            
        
        <label className="relative inline-flex h-7 w-12 cursor-pointer items-center" aria-label={`${title} an/aus`}>
        <input
          type="checkbox"
          className="peer sr-only"
          checked={enabled}
          onChange={(e) => onToggle(e.target.checked)}
        />
        <span className="h-full w-full rounded-full bg-slate-300 transition-colors peer-checked:bg-[color-mix(in_srgb,var(--accent)_35%,white)]" />
        <span className="pointer-events-none absolute left-1 h-5 w-5 rounded-full bg-white shadow transition-transform peer-checked:translate-x-5" />
        </label>
        </div>
        </header>
        <div>{children}</div>

    </section>
  );
};

export default ConfigCard;