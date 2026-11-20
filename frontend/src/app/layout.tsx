import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import AuthGate from "@/components/AuthGate";

export const metadata: Metadata = {
  title: "IPL Intelligence | Cricket Analytics & Agentic AI",
  description: "Historical IPL Data Warehouse, Interactive Dashboards & Hybrid RAG AI Assistant",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased">
        <Navbar />
        <main className="mx-auto max-w-7xl px-4 py-8">
          <AuthGate>{children}</AuthGate>
        </main>
      </body>
    </html>
  );
}