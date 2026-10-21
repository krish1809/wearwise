"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { NETWORK_ERROR, readApiError } from "@/lib/api/errors";

type Outcome = { ok: true } | { ok: false; message: string };

/**
 * A page a link in an email opens: it takes the token from the address and does one thing
 * with it. Unless `onLoad`, it waits for a click, so a mail app checking the link can't do it
 * for the person.
 */
export function EmailLinkPage({
  act,
  button,
  onLoad = false,
  done,
  failed,
}: {
  act: (token: string) => Promise<{ ok: boolean; error?: unknown }>;
  button?: string;
  onLoad?: boolean;
  done: React.ReactNode;
  failed: React.ReactNode;
}) {
  const token = useSearchParams().get("token") ?? "";
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [busy, setBusy] = useState(false);
  const started = useRef(false);

  async function run() {
    setBusy(true);
    try {
      const answer = await act(token);
      setOutcome(
        answer.ok
          ? { ok: true }
          : { ok: false, message: readApiError(answer.error).message },
      );
    } catch {
      setOutcome({ ok: false, message: NETWORK_ERROR });
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (onLoad && token && !started.current) {
      started.current = true;
      void run();
    }
    // Once per page: the token can't change while it's open, and `run` needn't be a dependency.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onLoad, token]);

  if (!token) {
    return <div className="mt-6">{failed}</div>;
  }
  if (outcome?.ok) {
    return <div className="mt-6 flex flex-col gap-4">{done}</div>;
  }
  return (
    <div className="mt-6 flex flex-col gap-4">
      {outcome && !outcome.ok && (
        <>
          <Alert tone="error">{outcome.message}</Alert>
          {failed}
        </>
      )}
      {!onLoad && !outcome && (
        <div>
          <Button onClick={() => void run()} loading={busy}>
            {button}
          </Button>
        </div>
      )}
      {onLoad && !outcome && (
        <p role="status" className="text-ink-soft">
          One moment…
        </p>
      )}
    </div>
  );
}
