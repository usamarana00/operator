type IconProps = {
  className?: string;
};

const base = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

/** The brand mark: a labeled apothecary jar. */
export function JarMark({ className }: IconProps) {
  return (
    <svg viewBox="0 0 32 40" className={className} {...base}>
      <path d="M12 2H20V7.5L24 11V36C24 37.66 22.66 39 21 39H11C9.34 39 8 37.66 8 36V11L12 7.5V2Z" />
      <path d="M8 18H24" />
      <rect x="13" y="22" width="6" height="9" rx="0.6" strokeWidth="1.4" />
    </svg>
  );
}

/** Sunrise glyph — the morning briefing. */
export function SunriseIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} {...base}>
      <path d="M4 18a8 8 0 0 1 16 0" />
      <path d="M12 3v3" />
      <path d="M4.5 8.5 6.6 10.6" />
      <path d="M19.5 8.5 17.4 10.6" />
      <path d="M2 21h20" />
      <path d="M6 21v-2M18 21v-2" />
    </svg>
  );
}

/** A folded, sealed label — the proposal. */
export function LabelIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} {...base}>
      <path d="M4 5.5A1.5 1.5 0 0 1 5.5 4h9l5 5v9.5A1.5 1.5 0 0 1 18 20H5.5A1.5 1.5 0 0 1 4 18.5Z" />
      <path d="M14.5 4v4.5H19" />
      <path d="M8 13h8M8 16.5h5" />
    </svg>
  );
}

export function UploadIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} {...base}>
      <path d="M12 16V4" />
      <path d="M7 9l5-5 5 5" />
      <path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" />
    </svg>
  );
}

export function CheckIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} {...base}>
      <path d="M5 12.5 10 17 19 7" />
    </svg>
  );
}

export function AlertIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} {...base}>
      <path d="M12 3 2 20h20L12 3Z" />
      <path d="M12 10v4" />
      <path d="M12 17.2v.1" />
    </svg>
  );
}

export function SignOutIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} {...base}>
      <path d="M9 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h3" />
      <path d="M16 17l5-5-5-5" />
      <path d="M21 12H9" />
    </svg>
  );
}

export function ChevronLeftIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} {...base}>
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

export function PlusIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} {...base}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function TrashIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} {...base}>
      <path d="M4 7h16" />
      <path d="M9 7V4.5A1.5 1.5 0 0 1 10.5 3h3A1.5 1.5 0 0 1 15 4.5V7" />
      <path d="M6 7l1 13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-13" />
    </svg>
  );
}

export function ShelfIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} {...base}>
      <path d="M4 5h16" />
      <path d="M4 13h16" />
      <path d="M6 5v6M11 5v6M18 5v6" />
      <path d="M6 13v6M11 13v6M18 13v6" />
    </svg>
  );
}

export function BranchIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} {...base}>
      <circle cx="6" cy="6" r="2.2" />
      <circle cx="6" cy="18" r="2.2" />
      <circle cx="18" cy="10" r="2.2" />
      <path d="M6 8.2V15.8" />
      <path d="M6 8.2c0 4 3 4 7.8 4H16" />
    </svg>
  );
}

export function BeakerIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} {...base}>
      <path d="M9 3h6" />
      <path d="M10 3v6.5L4.8 18a1.6 1.6 0 0 0 1.4 2.4h11.6a1.6 1.6 0 0 0 1.4-2.4L14 9.5V3" />
      <path d="M7.5 15h9" />
    </svg>
  );
}

export function ScaleIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} {...base}>
      <path d="M12 3v18" />
      <path d="M6 6h12" />
      <path d="M6 6 3 12a3 3 0 0 0 6 0Z" />
      <path d="M18 6l-3 6a3 3 0 0 0 6 0Z" />
      <path d="M8 21h8" />
    </svg>
  );
}

export const GithubMark = ({ className }: IconProps) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24">
    <path
      fillRule="evenodd"
      clipRule="evenodd"
      d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"
    />
  </svg>
);
