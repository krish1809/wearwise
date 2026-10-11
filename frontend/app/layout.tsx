import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WearWise",
  description:
    "Know what to wear, see what your wardrobe is missing, and make every purchase count.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="antialiased">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
