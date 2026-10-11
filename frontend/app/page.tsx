import { HealthStatus } from "@/components/health-status";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center gap-3 px-4">
      <h1 className="text-3xl font-semibold tracking-tight">WearWise</h1>
      <HealthStatus />
    </main>
  );
}
