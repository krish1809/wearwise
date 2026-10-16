import { AppShell } from "@/components/app-shell";

// Every page in this group is for logged-in people. proxy.ts sends anyone without a session
// cookie to log in first; the shell checks the session with the API.
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
