import type { Metadata } from "next";
import { Bricolage_Grotesque, Instrument_Sans } from "next/font/google";

import { Toaster } from "@/components/ui/toast";
import { TooltipProvider } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import "./globals.css";
import { Providers } from "./providers";

// Self-hosted by next/font at build time; the browser never calls Google.
const display = Bricolage_Grotesque({
  subsets: ["latin"],
  weight: ["600"],
  variable: "--font-bricolage-grotesque",
});
const sans = Instrument_Sans({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-instrument-sans",
});

export const metadata: Metadata = {
  title: "WearWise",
  description:
    "Know what to wear, see what your wardrobe is missing, and make every purchase count.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={cn(display.variable, sans.variable, "antialiased")}
    >
      <body className="min-h-screen">
        <Providers>
          <TooltipProvider>{children}</TooltipProvider>
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
