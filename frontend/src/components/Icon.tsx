import type { CSSProperties } from "react";

const PATHS = {
  search: "M11 4a7 7 0 1 0 4.2 12.6l4.1 4.1 1.4-1.4-4.1-4.1A7 7 0 0 0 11 4zm0 2a5 5 0 1 1 0 10 5 5 0 0 1 0-10z",
  database: "M12 3c-4.4 0-8 1.3-8 3v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6c0-1.7-3.6-3-8-3zm6 15c0 .5-2.3 1.5-6 1.5S6 18.5 6 18v-2.3c1.5.8 3.8 1.3 6 1.3s4.5-.5 6-1.3V18zm0-4.5c0 .5-2.3 1.5-6 1.5s-6-1-6-1.5v-2.3c1.5.8 3.8 1.3 6 1.3s4.5-.5 6-1.3v2.3zM12 9c-3.7 0-6-1-6-1.5S8.3 6 12 6s6 1 6 1.5S15.7 9 12 9z",
  chart: "M4 20V4h2v14h14v2H4zm4-3V9h3v8H8zm5 0V5h3v12h-3zm5 0v-5h1.8v5H18z",
  download: "M12 3v10.2l3.6-3.6L17 11l-5 5-5-5 1.4-1.4L12 13.2V3zm-7 15h14v2H5v-2z",
  presentation: "M4 3h16v11H4V3zm2 2v7h12V5H6zm5 11h2v2.2l3.2 1.8-1 1.7L12 19.8l-3.2 1.9-1-1.7 3.2-1.8V16z",
  shield: "M12 2 4 5v6c0 5 3.4 9.4 8 11 4.6-1.6 8-6 8-11V5l-8-3zm-1 14-4-4 1.4-1.4L11 13.2l4.6-4.6L17 10l-6 6z",
  brain: "M9 2a3 3 0 0 0-3 3 3 3 0 0 0-2 2.8A3 3 0 0 0 4 13a3 3 0 0 0 2 2.8V18a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3zm6 0a3 3 0 0 0-3 3v13a3 3 0 0 0 6 0v-2.2A3 3 0 0 0 20 13a3 3 0 0 0 0-5.2A3 3 0 0 0 18 5a3 3 0 0 0-3-3z",
  bolt: "M13 2 4.5 13H11l-1 9 8.5-11H12l1-9z",
  info: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z",
  check: "M9 16.2l-3.5-3.5L4 14.2l5 5 11-11-1.4-1.4z",
  code: "M8.7 16.6 4.1 12l4.6-4.6L7.3 6 1.3 12l6 6 1.4-1.4zm6.6 0 4.6-4.6-4.6-4.6L16.7 6l6 6-6 6-1.4-1.4zM10 20l3-16h2l-3 16h-2z",
  refresh: "M12 5V1L7 6l5 5V7a5 5 0 1 1-5 5H5a7 7 0 1 0 7-7z",
  thumbUp: "M2 10h4v11H2V10zm20 1.5c0-1.4-1.1-2.5-2.5-2.5H14l.8-3.8.1-.8c0-.5-.2-1-.5-1.4L13.3 2 7.6 7.7C7.2 8.1 7 8.6 7 9.2V18c0 1.1.9 2 2 2h7.5c.8 0 1.5-.5 1.8-1.2l3.5-5.8c.1-.3.2-.6.2-1v-.5z",
  thumbDown: "M22 14h-4V3h4v11zM2 12.5C2 13.9 3.1 15 4.5 15H10l-.8 3.8-.1.8c0 .5.2 1 .5 1.4l1.1 1 5.7-5.7c.4-.4.6-.9.6-1.5V6c0-1.1-.9-2-2-2H7.5c-.8 0-1.5.5-1.8 1.2L2.2 11c-.1.3-.2.6-.2 1v.5z",
  close: "M6.4 5 12 10.6 17.6 5 19 6.4 13.4 12 19 17.6 17.6 19 12 13.4 6.4 19 5 17.6 10.6 12 5 6.4z",
} as const;

export type IconName = keyof typeof PATHS;

interface IconProps {
  name: IconName;
  size?: number;
  color?: string;
  style?: CSSProperties;
  className?: string;
}

export default function Icon({ name, size = 17, color = "currentColor", style, className }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={color}
      style={style}
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
