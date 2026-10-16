"use client";

import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { type ApiProblem, problemFrom } from "@/lib/api/errors";
import {
  type Profile,
  type ProfileChanges,
  type Reference,
  useSaveProfile,
} from "@/lib/profile";

/**
 * What every profile section form takes. The same forms appear in onboarding (with Back,
 * Skip, and Continue) and in Settings (with Save and Clear); only the buttons differ.
 */
export type SectionFormProps = {
  profile: Profile;
  reference: Reference;
  /** Sent with every save, such as how far onboarding got. */
  alsoSave?: ProfileChanges;
  onSaved?: (profile: Profile) => void;
  /** The buttons under the form. A submit button saves. */
  actions: (state: { saving: boolean }) => React.ReactNode;
};

/** Saving a section: the API's messages, and whether a save is running. */
export function useSectionSave({
  alsoSave,
  onSaved,
}: Pick<SectionFormProps, "alsoSave" | "onSaved">) {
  const save = useSaveProfile();
  const [problem, setProblem] = useState<ApiProblem | null>(null);

  async function submit(changes: ProfileChanges) {
    setProblem(null);
    try {
      const profile = await save.mutateAsync({ ...changes, ...alsoSave });
      onSaved?.(profile);
    } catch (error) {
      setProblem(problemFrom(error));
    }
  }

  return {
    submit,
    saving: save.isPending,
    problem,
    /** The API's message for one field, if it sent one. */
    apiError: (field: string): string | undefined => problem?.fields[field],
  };
}

type SectionFormFrameProps = {
  onSubmit: () => void;
  problem: ApiProblem | null;
  /** True when the browser found mistakes before sending anything. */
  hasErrors?: boolean;
  actions: React.ReactNode;
  children: React.ReactNode;
};

export function SectionFormFrame({
  onSubmit,
  problem,
  hasErrors = false,
  actions,
  children,
}: SectionFormFrameProps) {
  return (
    <form
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
      className="flex flex-col gap-7"
    >
      {problem && <Alert tone="error">{problem.message}</Alert>}
      {hasErrors && !problem && (
        <Alert tone="error">Check the highlighted fields.</Alert>
      )}
      {children}
      {actions}
    </form>
  );
}
