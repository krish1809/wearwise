"use client";

import Link from "next/link";

import { PageLoading } from "@/components/app-shell";
import { TextLink } from "@/components/text-link";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { toast } from "@/components/ui/toast";
import { problemFrom } from "@/lib/api/errors";
import { useCurrentUser } from "@/lib/auth";
import { useDismissOnboardingReminder, useProfile } from "@/lib/profile";

export function HomeContent() {
  const { data: user } = useCurrentUser();
  if (!user) return <PageLoading />;
  const firstName = user.name?.split(/\s+/)[0];

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          {firstName ? `Hello, ${firstName}` : "Hello"}
        </h1>
        <p className="mt-3 max-w-prose text-ink-soft">
          You&apos;re logged in as {user.email}. Your profile, sizes, and
          account are in <TextLink href="/settings">Settings</TextLink>.
        </p>
      </div>
      <FinishSetup />
    </div>
  );
}

/** Shown once onboarding was skipped, until the person finishes it or says not now. */
function FinishSetup() {
  const { data: profile } = useProfile();
  const dismiss = useDismissOnboardingReminder();
  if (!profile?.show_onboarding_reminder) return null;

  return (
    <Card className="flex flex-col gap-4">
      <div>
        <CardTitle>Finish setting up WearWise</CardTitle>
        <CardDescription className="mt-1 max-w-prose">
          Your sizes, style, and budget help WearWise suggest what suits you.
          Every question is optional.
        </CardDescription>
      </div>
      <div className="flex flex-wrap gap-3">
        <Button asChild>
          <Link href="/onboarding">Finish setup</Link>
        </Button>
        <Button
          variant="quiet"
          loading={dismiss.isPending}
          onClick={() =>
            dismiss.mutate(undefined, {
              onError: (error) => toast.error(problemFrom(error).message),
            })
          }
        >
          Not now
        </Button>
      </div>
    </Card>
  );
}
