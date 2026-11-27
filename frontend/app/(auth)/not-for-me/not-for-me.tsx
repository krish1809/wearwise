"use client";

import { EmailLinkPage } from "@/components/email-link-page";
import { TextLink } from "@/components/text-link";
import { api } from "@/lib/api/client";

export function NotForMe() {
  return (
    <EmailLinkPage
      button="Not for me"
      act={async (token) => {
        const { error, response } = await api.POST("/api/v1/email/not-for-me", {
          body: { token },
        });
        return { ok: response.ok, error };
      }}
      done={
        <p>
          Noted. <TextLink href="/picks">See your picks</TextLink>, where you
          can also take it back.
        </p>
      }
      failed={
        <p>
          You can also say &ldquo;Not for me&rdquo; on the{" "}
          <TextLink href="/picks">Weekly picks</TextLink> page.
        </p>
      }
    />
  );
}
