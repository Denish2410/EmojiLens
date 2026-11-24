export function Logo({ className = "size-7" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" aria-hidden="true" className={className}>
      <defs>
        <linearGradient id="el-g" x1="4" y1="4" x2="26" y2="26" gradientUnits="userSpaceOnUse">
          <stop stopColor="#8b5cf6" />
          <stop offset="1" stopColor="#22d3ee" />
        </linearGradient>
      </defs>
      <circle cx="14" cy="14" r="9" stroke="url(#el-g)" strokeWidth="3" />
      <path d="M20.5 20.5 27 27" stroke="url(#el-g)" strokeWidth="3.2" strokeLinecap="round" />
      <path
        d="M10.5 11v6M14 11v6M17.5 11v6"
        stroke="#22d3ee"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeDasharray="1.2 2"
      />
    </svg>
  );
}
