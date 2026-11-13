import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Keplix Replayer | Orbit Mission Control",
  description: "Interactive React Flow trace and state graph replay viewer for Keplix multi-agent runs",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased bg-slate-950 text-slate-100">{children}</body>
    </html>
  );
}

