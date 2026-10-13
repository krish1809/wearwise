"use client";

import { useState } from "react";

import { PageLoading } from "@/components/app-shell";
import { BrandNotes } from "@/components/profile/brand-notes";
import {
  PROFILE_SECTIONS,
  type ProfileSection,
} from "@/components/profile/sections";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "@/components/ui/toast";
import { problemFrom } from "@/lib/api/errors";
import { type User, useCurrentUser } from "@/lib/auth";
import {
  clearing,
  type Profile,
  type ProfileChanges,
  type Reference,
  useProfile,
  useReference,
  useSaveProfile,
} from "@/lib/profile";

import { DeleteAccountDialog } from "./delete-account-dialog";
import { NameForm } from "./name-form";

// Which profile sections each tab shows, by section id.
const TABS = [
  {
    value: "profile",
    label: "Profile",
    sections: ["about", "sizes", "measurements"],
  },
  { value: "style", label: "Style", sections: ["occasions", "style"] },
  { value: "budget", label: "Budget", sections: ["budget"] },
] as const;

export function SettingsContent() {
  const { data: user } = useCurrentUser();
  if (!user) return <PageLoading />;

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <h1 className="font-display text-2xl font-semibold tracking-tight">
        Settings
      </h1>
      <Tabs defaultValue="profile">
        <TabsList aria-label="Settings sections" className="gap-x-2 sm:gap-x-4">
          {TABS.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value}>
              {tab.label}
            </TabsTrigger>
          ))}
          <TabsTrigger value="brands">Brands</TabsTrigger>
          <TabsTrigger value="account">Account</TabsTrigger>
        </TabsList>
        {TABS.map((tab) => (
          <TabsContent key={tab.value} value={tab.value}>
            <ProfileTab sectionIds={tab.sections} />
          </TabsContent>
        ))}
        <TabsContent value="brands">
          <p className="mb-4 max-w-prose text-ink-soft">
            Sizes differ between brands. Keep a note of what fits you at each
            one, and how its quality and prices compare.
          </p>
          <BrandNotes />
        </TabsContent>
        <TabsContent value="account">
          <AccountTab user={user} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ProfileTab({ sectionIds }: { sectionIds: readonly string[] }) {
  const profile = useProfile();
  const reference = useReference();

  if (profile.isError || reference.isError) {
    return (
      <ErrorState
        title="Couldn't load your profile"
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
  if (!profile.data || !reference.data) {
    return (
      <div aria-busy="true" className="flex flex-col gap-4">
        <Skeleton className="h-48" />
        <Skeleton className="h-48" />
        <span role="status" className="sr-only">
          Loading
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {PROFILE_SECTIONS.filter((section) =>
        sectionIds.includes(section.id),
      ).map((section) => (
        <SectionCard
          key={section.id}
          section={section}
          profile={profile.data}
          reference={reference.data}
        />
      ))}
    </div>
  );
}

/** One profile section with Save, and Clear with an undo. */
function SectionCard({
  section,
  profile,
  reference,
}: {
  section: ProfileSection;
  profile: Profile;
  reference: Reference;
}) {
  // Changing the key redraws the form from the saved profile, after Clear or Undo.
  const [version, setVersion] = useState(0);
  const save = useSaveProfile();

  async function replace(changes: ProfileChanges, done: () => void) {
    try {
      await save.mutateAsync(changes);
      setVersion((current) => current + 1);
      done();
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  function clear() {
    const before = Object.fromEntries(
      section.fields.map((field) => [field, profile[field as keyof Profile]]),
    ) as ProfileChanges;
    void replace(clearing(section.fields), () =>
      toast.success(`${section.title} cleared`, {
        action: {
          label: "Undo",
          onClick: () =>
            void replace(before, () =>
              toast.success(`${section.title} restored`),
            ),
        },
      }),
    );
  }

  return (
    <Card>
      <CardTitle>{section.title}</CardTitle>
      <CardDescription className="mt-1">{section.intro}</CardDescription>
      <div className="mt-6">
        <section.Form
          key={version}
          profile={profile}
          reference={reference}
          onSaved={() => toast.success(`${section.title} saved`)}
          actions={({ saving }) => (
            <div className="flex flex-wrap gap-3">
              <Button type="submit" loading={saving} disabled={save.isPending}>
                Save
              </Button>
              <Button
                type="button"
                variant="quiet"
                loading={save.isPending}
                disabled={saving}
                onClick={clear}
              >
                Clear answers
              </Button>
            </div>
          )}
        />
      </div>
    </Card>
  );
}

function AccountTab({ user }: { user: User }) {
  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardTitle>Account</CardTitle>
        <div className="mt-4 flex flex-col gap-5">
          <NameForm user={user} />
          <div className="flex flex-col gap-1">
            <p className="text-sm font-medium">Email</p>
            <p className="break-all">{user.email}</p>
          </div>
        </div>
      </Card>

      <Card>
        <CardTitle>Delete account</CardTitle>
        <CardDescription className="mt-1">
          Removes your account and everything in it, including your profile and
          brand notes. This can&apos;t be undone.
        </CardDescription>
        <div className="mt-4">
          <DeleteAccountDialog email={user.email} />
        </div>
      </Card>
    </div>
  );
}
