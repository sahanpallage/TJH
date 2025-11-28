import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "TJH Job Hunter",
  description: "A polished job search UI for JSearch and TheirStack.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-gradient-to-br from-[#020617] via-[#020617] to-[#0f172a] text-zinc-50 min-h-screen`}
      >
        <div className="relative overflow-hidden">
          <div className="pointer-events-none fixed inset-0 -z-10">
            <div className="absolute -top-40 -left-40 h-80 w-80 rounded-full bg-blue-500/20 blur-3xl" />
            <div className="absolute top-1/2 -right-40 h-96 w-96 rounded-full bg-emerald-500/10 blur-3xl" />
            <div className="absolute -bottom-40 left-1/2 h-72 w-72 -translate-x-1/2 rounded-full bg-indigo-500/20 blur-3xl" />
          </div>

          <header className="border-b border-white/5 bg-black/20 backdrop-blur-md sticky top-0 z-20">
            <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
              <div className="flex items-center gap-2">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-blue-500 via-sky-400 to-emerald-400 shadow-[0_0_25px_rgba(56,189,248,0.75)]">
                  <span className="text-xs font-black tracking-[0.18em] text-white">
                    TJH
                  </span>
                </div>
                <div>
                  <p className="text-sm font-semibold tracking-tight">
                    TJH Job Hunter
                  </p>
                  <p className="text-[11px] text-zinc-400">
                    JSearch & TheirStack, one sleek interface
                  </p>
                </div>
              </div>

              <div className="hidden items-center gap-3 text-xs text-zinc-400 sm:flex">
                <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 font-medium text-emerald-300">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_12px_rgba(52,211,153,0.9)]" />
                  Live job insights
                </span>
                <span className="hidden md:inline text-zinc-500">•</span>
                <span className="hidden md:inline">
                  Designed for fast, focused job discovery
                </span>
              </div>
            </div>
          </header>

          <main>{children}</main>

          <footer className="border-t border-white/5 bg-black/30 backdrop-blur-sm">
            <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-4 py-4 text-xs text-zinc-500 sm:flex-row sm:px-6 lg:px-8">
              <p>Built for technical job hunters.</p>
              <p className="text-[11px]">
                Powered by <span className="font-medium text-zinc-300">JSearch</span>{" "}
                & <span className="font-medium text-zinc-300">TheirStack</span>
              </p>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
