import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PHANTOM TRADE — Supply Chain Intelligence",
  description: "Fake signals move real markets. We stop them first.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased" style={{ colorScheme: "dark" }}>
      <body className="min-h-full flex flex-col" style={{ background: "#0A0A0F" }}>
        {children}
      </body>
    </html>
  );
}
