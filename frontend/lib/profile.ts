import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { ApiRequestError, readApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";
import { meQueryKey, type User } from "@/lib/auth";

export type Profile = components["schemas"]["ProfileOut"];
export type ProfileChanges = components["schemas"]["ProfileUpdate"];
export type Reference = components["schemas"]["ReferenceOut"];
export type ColorFamily = components["schemas"]["ColorFamilyOut"];

export const profileQueryKey = ["profile"] as const;
export const referenceQueryKey = ["reference"] as const;

// The number of onboarding steps; the backend checks the same number.
export const ONBOARDING_STEPS = 6;

/** The lists the forms offer. They change only when the app is deployed. */
export function useReference() {
  return useQuery({
    queryKey: referenceQueryKey,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/reference");
      if (data) return data;
      throw new ApiRequestError(readApiError(error));
    },
    staleTime: Infinity,
  });
}

export function useProfile() {
  return useQuery({
    queryKey: profileQueryKey,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/profile");
      if (data) return data;
      throw new ApiRequestError(readApiError(error));
    },
    staleTime: 5 * 60_000,
  });
}

/** Save some answers. Only the fields given change; null clears one. */
export function useSaveProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (changes: ProfileChanges) => {
      const { data, error } = await api.PATCH("/api/v1/profile", {
        body: changes,
      });
      if (data) return data;
      throw new ApiRequestError(readApiError(error));
    },
    onSuccess: (profile) => {
      queryClient.setQueryData(profileQueryKey, profile);
    },
  });
}

/** Mark onboarding done. `skipped` is true for "Skip all", so Home offers to finish later. */
export function useFinishOnboarding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (skipped: boolean) => {
      const { error, response } = await api.POST("/api/v1/onboarding/finish", {
        body: { skipped },
      });
      if (!response.ok) throw new ApiRequestError(readApiError(error));
    },
    onSuccess: async () => {
      queryClient.setQueryData<User | null>(meQueryKey, (user) =>
        user ? { ...user, onboarding_completed: true } : user,
      );
      await queryClient.invalidateQueries({ queryKey: profileQueryKey });
    },
  });
}

export function useDismissOnboardingReminder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { error, response } = await api.POST(
        "/api/v1/onboarding/reminder/dismiss",
      );
      if (!response.ok) throw new ApiRequestError(readApiError(error));
    },
    onSuccess: () => {
      queryClient.setQueryData<Profile>(profileQueryKey, (profile) =>
        profile ? { ...profile, show_onboarding_reminder: false } : profile,
      );
    },
  });
}

/** Changes that clear the given fields. */
export function clearing(
  fields: readonly (keyof ProfileChanges)[],
): ProfileChanges {
  return Object.fromEntries(fields.map((field) => [field, null]));
}
