"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { PageLoading } from "@/components/app-shell";
import { PROFILE_SECTIONS } from "@/components/profile/sections";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { problemFrom } from "@/lib/api/errors";
import { useCurrentUser } from "@/lib/auth";
import {
  ONBOARDING_STEPS,
  type Profile,
  type Reference,
  useFinishOnboarding,
  useProfile,
  useReference,
  useSaveProfile,
} from "@/lib/profile";
import { cn } from "@/lib/utils";

type Action = "continue" | "skip" | "all";

/**
 * Six short steps, each optional. Continue saves the step; Skip moves on without saving;
 * Skip all ends onboarding at once. The step reached is saved, so closing the tab loses nothing.
 */
export function OnboardingFlow() {
  const router = useRouter();
  const user = useCurrentUser();
  const profile = useProfile();
  const reference = useReference();

  useEffect(() => {
    if (user.data === null) router.replace("/login?next=/onboarding");
  }, [user.data, router]);

  if (profile.isError || reference.isError) {
    return (
      <ErrorState
        className="mx-auto max-w-md"
        title="Couldn't reach WearWise"
        action={
          <Button
            variant="secondary"
            onClick={() => {
              void profile.refetch();
              void reference.refetch();
            }}
          >
            Try again
          </Button>
        }
      >
        Check your connection and try again.
      </ErrorState>
    );
  }
  if (!profile.data || !reference.data) return <PageLoading />;
  return <Steps profile={profile.data} reference={reference.data} />;
}

function Steps({
  profile,
  reference,
}: {
  profile: Profile;
  reference: Reference;
}) {
  const router = useRouter();
  const saveProfile = useSaveProfile();
  const finish = useFinishOnboarding();
  // Start where the person left off; someone who finished before starts again at the top.
  const [step, setStep] = useState(() =>
    profile.onboarding_step >= ONBOARDING_STEPS ? 0 : profile.onboarding_step,
  );
  const [error, setError] = useState<string | null>(null);
  const [action, setAction] = useState<Action | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const firstStep = useRef(true);

  // Each new step is a new screen: move focus to its heading so screen readers announce it.
  useEffect(() => {
    if (firstStep.current) {
      firstStep.current = false;
      return;
    }
    window.scrollTo({ top: 0 });
    headingRef.current?.focus();
  }, [step]);

  const section = PROFILE_SECTIONS[step];
  const isLast = step === ONBOARDING_STEPS - 1;

  /** Run one of the buttons' actions; on success the flow moves on, so `action` stays set. */
  async function run(kind: Action, work: () => Promise<void>) {
    setError(null);
    setAction(kind);
    try {
      await work();
    } catch (failure) {
      setError(problemFrom(failure).message);
      setAction(null);
    }
  }

  async function advance(from: number) {
    if (from === ONBOARDING_STEPS - 1) {
      await finish.mutateAsync(false);
      router.replace("/home");
      return;
    }
    setStep(from + 1);
    setAction(null);
  }

  const skipAll = () =>
    run("all", async () => {
      await finish.mutateAsync(true);
      router.replace("/home");
    });

  // Only the step reached is saved; the answers on this screen stay as they were.
  const skipStep = (from: number) =>
    run("skip", async () => {
      await saveProfile.mutateAsync({ onboarding_step: from + 1 });
      await advance(from);
    });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm font-medium text-ink-soft">
          Step {step + 1} of {ONBOARDING_STEPS}
        </p>
        {step === 0 && (
          <Button
            variant="quiet"
            className="-mr-4"
            loading={action === "all"}
            disabled={action !== null}
            onClick={() => void skipAll()}
          >
            Skip all
          </Button>
        )}
      </div>
      <Progress step={step} />
      <div>
        <h1
          ref={headingRef}
          tabIndex={-1}
          className="font-display text-2xl font-semibold tracking-tight outline-none"
        >
          {section.title}
        </h1>
        <p className="mt-2 text-ink-soft">{section.intro}</p>
      </div>
      {error && <Alert tone="error">{error}</Alert>}
      <section.Form
        key={section.id}
        profile={profile}
        reference={reference}
        alsoSave={{ onboarding_step: step + 1 }}
        onSaved={() => void run("continue", () => advance(step))}
        actions={({ saving }) => (
          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:items-center">
            {step > 0 && (
              <Button
                type="button"
                variant="quiet"
                className="sm:mr-auto sm:-ml-4"
                disabled={action !== null || saving}
                onClick={() => setStep(step - 1)}
              >
                Back
              </Button>
            )}
            <Button
              type="button"
              variant="secondary"
              className={cn(step === 0 && "sm:ml-auto")}
              loading={action === "skip"}
              disabled={action !== null || saving}
              onClick={() => void skipStep(step)}
            >
              Skip this step
            </Button>
            <Button
              type="submit"
              loading={saving || action === "continue"}
              disabled={action !== null}
            >
              {isLast ? "Finish" : "Continue"}
            </Button>
          </div>
        )}
      />
    </div>
  );
}

function Progress({ step }: { step: number }) {
  return (
    <div aria-hidden className="flex gap-1.5">
      {Array.from({ length: ONBOARDING_STEPS }, (_, index) => (
        <span
          key={index}
          className={cn(
            "h-1.5 flex-1 rounded-full",
            index <= step ? "bg-indigo" : "bg-line",
          )}
        />
      ))}
    </div>
  );
}
