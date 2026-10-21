import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { ApiRequestError, readApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

export type Digest = components["schemas"]["DigestOut"];
export type DigestPick = components["schemas"]["PickOut"];

export const digestQueryKey = ["digest", "latest"] as const;

/** The latest weekly picks; null before there are any. */
export function useLatestDigest() {
  return useQuery({
    queryKey: digestQueryKey,
    queryFn: async (): Promise<Digest | null> => {
      const { data, error, response } = await api.GET("/api/v1/digests/latest");
      if (data !== undefined) return data;
      if (response.status === 404) return null;
      throw new ApiRequestError(readApiError(error));
    },
  });
}

/** Work out this week's picks now, without emailing them. */
export function useWorkOutPicks() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<Digest> => {
      const { data, error } = await api.POST("/api/v1/digests/preview");
      if (data !== undefined) return data;
      throw new ApiRequestError(readApiError(error));
    },
    onSuccess: (digest) => queryClient.setQueryData(digestQueryKey, digest),
  });
}

/** "Not for me", or taking it back. */
export function useNotForMe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      notForMe,
    }: {
      id: string;
      notForMe: boolean;
    }): Promise<Digest> => {
      const path = "/api/v1/digest-picks/{pick_id}/not-for-me";
      const options = { params: { path: { pick_id: id } } };
      const { data, error } = notForMe
        ? await api.POST(path, options)
        : await api.DELETE(path, options);
      if (data !== undefined) return data;
      throw new ApiRequestError(readApiError(error));
    },
    onSuccess: (digest) => queryClient.setQueryData(digestQueryKey, digest),
  });
}

export type DigestSettings = components["schemas"]["DigestSettingsOut"];

const settingsQueryKey = ["digest", "settings"] as const;

export const WEEKDAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

export function useDigestSettings() {
  return useQuery({
    queryKey: settingsQueryKey,
    queryFn: async (): Promise<DigestSettings> => {
      const { data, error } = await api.GET("/api/v1/digest-settings");
      if (data !== undefined) return data;
      throw new ApiRequestError(readApiError(error));
    },
  });
}

type SettingsChange =
  | { action: "on"; weekday: number }
  | { action: "off" }
  | { action: "day"; weekday: number };

/** Turn the weekly email on (a confirmation link goes out first if the address isn't
 * confirmed yet), off, or move it to another day. */
export function useChangeDigestSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (change: SettingsChange): Promise<DigestSettings> => {
      const answer =
        change.action === "on"
          ? await api.POST("/api/v1/digest-settings/on", {
              body: { weekday: change.weekday },
            })
          : change.action === "off"
            ? await api.POST("/api/v1/digest-settings/off")
            : await api.PATCH("/api/v1/digest-settings", {
                body: { weekday: change.weekday },
              });
      if (answer.data !== undefined) return answer.data;
      throw new ApiRequestError(readApiError(answer.error));
    },
    onSuccess: (found) => queryClient.setQueryData(settingsQueryKey, found),
  });
}
