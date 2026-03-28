import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "PixelForge — Computer Vision Image Tools",
  description:
    "Transform your photos with pure computer vision. Background removal, image enhancement, and sketch/cartoon conversion — zero AI APIs, powered by OpenCV.",
  keywords: ["image processing", "computer vision", "OpenCV", "background removal", "image enhancement"],
  authors: [{ name: "PixelForge" }],
  openGraph: {
    title: "PixelForge — Computer Vision Image Tools",
    description: "Transform your photos with pure computer vision — zero AI APIs.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      {/* Inline script runs before paint — prevents flash of wrong theme */}
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){var t=localStorage.getItem('pf-theme');if(t!=='light')document.documentElement.classList.add('dark');})();`,
          }}
        />
      </head>
      <body className="min-h-screen font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
