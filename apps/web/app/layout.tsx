import type { Metadata } from "next";
import "./globals.css";
import { UIProviders } from "@/components/providers/ui-providers";

export const metadata: Metadata = {
  title: "DreamAxis",
  description: "Local-first AI execution platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <UIProviders>{children}</UIProviders>
      </body>
    </html>
  );
}
