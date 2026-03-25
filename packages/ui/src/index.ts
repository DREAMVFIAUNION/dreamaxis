export const dreamAxisTheme = {
  colors: {
    background: "#111111",
    surface: "#171717",
    surfaceRaised: "#202020",
    surfaceMuted: "#262626",
    border: "#303030",
    text: "#F5F5F5",
    textMuted: "#9CA3AF",
    primary: "#00D4FF",
    primarySoft: "#A8E8FF",
    warning: "#F7C66A",
    danger: "#F38BA8",
    success: "#4ADE80",
  },
  radius: {
    panel: "0px",
  },
} as const;

export const moduleNavigation = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/chat/local-demo", label: "Chat" },
  { href: "/operator", label: "Operator" },
  { href: "/knowledge", label: "Knowledge" },
  { href: "/skills", label: "Skills" },
  { href: "/runtime", label: "Runtime" },
  { href: "/environment", label: "Doctor" },
  { href: "/logs", label: "Logs" },
  { href: "/governance", label: "Governance" },
] as const;
