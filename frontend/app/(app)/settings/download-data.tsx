"use client";

import { Download } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/toast";
import { readApiError } from "@/lib/api/errors";

const FAILED = "Couldn't make the file. Check your connection and try again.";

/** Everything stored for the account, as one zip file: the data as JSON, and every photo. */
export function DownloadData() {
  const [busy, setBusy] = useState(false);

  async function download() {
    setBusy(true);
    try {
      const response = await fetch("/api/v1/account/export");
      if (!response.ok) {
        const body: unknown = await response.json().catch(() => null);
        toast.error(body ? readApiError(body).message : FAILED);
        return;
      }
      const name =
        /filename="([^"]+)"/.exec(
          response.headers.get("content-disposition") ?? "",
        )?.[1] ?? "wearwise.zip";
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = name;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error(FAILED);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Button variant="secondary" loading={busy} onClick={() => void download()}>
      <Download aria-hidden />
      Download my data
    </Button>
  );
}
