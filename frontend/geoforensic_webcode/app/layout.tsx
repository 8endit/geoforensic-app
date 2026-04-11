import type { Metadata } from "next";
import { Geist_Mono } from "next/font/google";
import { Toaster } from "sonner";

import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";
import { Header } from "@/components/header";

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "geoforensic",
  description: "Bodenbewegung, Hochwasserrisiko und Bauvorhaben — in einem Report für Ihre Immobilie."
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de">
      <body
        className={`${geistMono.variable} antialiased`}
        suppressHydrationWarning
      >
        <AuthProvider>
          <Header />
          {children}
          <Toaster position="top-right" richColors />
        </AuthProvider>
      </body>
    </html>
  );
}
