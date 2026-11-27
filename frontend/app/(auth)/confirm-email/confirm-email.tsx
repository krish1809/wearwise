"use client";

import { EmailLinkPage } from "@/components/email-link-page";
import { TextLink } from "@/components/text-link";
import { api } from "@/lib/api/client";

export function ConfirmEmail() {
  return (
    <EmailLinkPage
      onLoad
      act={async (token) => {
        const { error, response } = await api.POST(
          "/api/v1/auth/confirm-email",
          {
            body: { token },
          },
        );
        return { ok: response.ok, error };
      }}
      done={
        <>
          <p>
            Your address is confirmed, and the weekly email is on. Change the
            day or turn it off in Settings.
          </p>
          <p>
            <TextLink href="/picks">See this week&apos;s picks</TextLink>
          </p>
        </>
      }
      failed={
        <p>
          Turn the email on again in{" "}
          <TextLink href="/settings">Settings</TextLink> to get a new link.
        </p>
      }
    />
  );
}
