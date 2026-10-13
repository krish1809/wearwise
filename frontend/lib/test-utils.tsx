import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";

/** Render with a fresh query cache, and return the cache so a test can look inside it. */
export function renderWithQueries(ui: React.ReactElement): QueryClient {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
  return client;
}

export function typeInto(label: string, value: string): void {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

/** What the typed API client resolves with, for mocking it. */
export function apiAnswer(
  status: number,
  body?: unknown,
): { data?: unknown; error?: unknown; response: Response } {
  const ok = status >= 200 && status < 300;
  return {
    data: ok ? body : undefined,
    error: ok ? undefined : body,
    response: new Response(null, { status }),
  };
}

/** The JSON body a mocked API method was called with, by call number. */
export function sentBody(
  spy: { mock: { calls: unknown[][] } },
  call = 0,
): unknown {
  return (spy.mock.calls[call]?.[1] as { body?: unknown } | undefined)?.body;
}
