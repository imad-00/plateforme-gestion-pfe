import type { Metadata } from "next";
import { Fraunces, Hanken_Grotesk, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";

// App-wide UI sans — used everywhere except the landing page.
const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
});

// Landing-page typefaces. Exposed as CSS variables so they only render where
// landing.css references them — pay the byte cost once, no spill into the app.
const fraunces = Fraunces({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-fraunces",
  display: "swap",
});

const hanken = Hanken_Grotesk({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-hanken",
  display: "swap",
});

const jbmono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-jbmono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "GradeX — PFE Management Platform · ESI-SBA",
  description:
    "GradeX is the single platform where ESI-SBA (École Supérieure en Informatique de Sidi Bel Abbès) students, professors, and juries manage final-year projects (PFE) — from subject proposal to final defense.",
  keywords: [
    "ESI-SBA",
    "École Supérieure en Informatique",
    "Sidi Bel Abbès",
    "PFE",
    "Projet de Fin d'Études",
    "GradeX",
    "academic platform",
  ],
  openGraph: {
    title: "GradeX — PFE Management Platform · ESI-SBA",
    description:
      "Final-year project (PFE) management platform for the École Supérieure en Informatique de Sidi Bel Abbès.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${fraunces.variable} ${hanken.variable} ${jbmono.variable} h-full antialiased`}
    >
      <body className="h-full">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
