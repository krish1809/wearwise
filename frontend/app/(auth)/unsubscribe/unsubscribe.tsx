"use client";

import { EmailLinkPage } from "@/components/email-link-page";
import { TextLink } from "@/components/text-link";
import { api } from "@/lib/api/client";

export function Unsubscribe() {
  return (
    <EmailLinkPage
      button="Stop the weekly email"
      act={async (token) => {
        const { error, response } = await api.POST(
          "/api/v1/email/unsubscribe",
          {
            body: { token },
          },
        );
        return { ok: response.ok, error };
      }}
      done={
        <p>
          Done: no more weekly emails. You can turn it on again in{" "}
          <TextLink href="/settings">Settings</TextLink>.
        </p>
      }
      failed={
        <p>
          You can also turn the email off in{" "}
          <TextLink href="/settings">Settings</TextLink>.
        </p>
      }
    />
  );
}
