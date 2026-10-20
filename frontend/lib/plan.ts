import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { ApiRequestError, readApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

export type Week = components["schemas"]["WeekOut"];
export type PlanDay = components["schemas"]["PlanDayOut"];
export type DayOption = components["schemas"]["OptionOut"];
export type PlanEvent = components["schemas"]["EventOut"];
export type NewEvent = components["schemas"]["EventIn"];
export type Laundry = components["schemas"]["LaundryOut"];

const weekKey = (start: string) => ["plan", start] as const;

async function ok<T>(
  request: Promise<{ data?: T; error?: unknown }>,
): Promise<T> {
  const { data, error } = await request;
  if (data !== undefined) return data;
  throw new ApiRequestError(readApiError(error));
}

export function useWeek(start: string) {
  return useQuery({
    queryKey: weekKey(start),
    queryFn: () =>
      ok(api.GET("/api/v1/plan", { params: { query: { start } } })),
  });
}

/** Plan every day that isn't locked or worn. */
export function usePlanWeek(start: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      ok(api.POST("/api/v1/plan/generate", { body: { start } })),
    onSuccess: (week) => queryClient.setQueryData(weekKey(start), week),
  });
}

/** Put one day's new state into the cached week. */
function useReplaceDay(start: string) {
  const queryClient = useQueryClient();
  return (day: PlanDay) =>
    queryClient.setQueryData<Week>(weekKey(start), (week) =>
      week
        ? {
            ...week,
            days: week.days.map((d) => (d.day === day.day ? day : d)),
          }
        : week,
    );
}

export function useChangeDay(start: string) {
  const replace = useReplaceDay(start);
  return useMutation({
    mutationFn: ({
      day,
      changes,
    }: {
      day: string;
      changes: components["schemas"]["DayChange"];
    }) =>
      ok(
        api.PATCH("/api/v1/plan/days/{day}", {
          params: { path: { day }, query: { start } },
          body: changes,
        }),
      ),
    onSuccess: replace,
  });
}

export function useDayOptions(start: string, day: string | null) {
  return useQuery({
    queryKey: ["plan-options", start, day],
    queryFn: () =>
      ok(
        api.GET("/api/v1/plan/days/{day}/options", {
          params: { path: { day: day ?? "" }, query: { start } },
        }),
      ),
    enabled: day !== null,
    staleTime: 0,
  });
}

/** Log the day's outfit as worn: the wear log, wear counts, and laundry change too. */
export function useWearDay(start: string) {
  const replace = useReplaceDay(start);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (day: string) =>
      ok(
        api.POST("/api/v1/plan/days/{day}/wear", {
          params: { path: { day } },
        }),
      ),
    onSuccess: async (day) => {
      replace(day);
      await Promise.all(
        [["wear-logs"], ["items"], ["item"], ["outfits"], ["laundry"]].map(
          (queryKey) => queryClient.invalidateQueries({ queryKey }),
        ),
      );
    },
  });
}

export function useEvents() {
  return useQuery({
    queryKey: ["events"],
    queryFn: () => ok(api.GET("/api/v1/events")),
  });
}

/** Events change a day's occasion: refresh the plan too. */
function useRefreshEvents() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all(
      [["events"], ["plan"]].map((queryKey) =>
        queryClient.invalidateQueries({ queryKey }),
      ),
    );
}

export function useCreateEvent() {
  const refresh = useRefreshEvents();
  return useMutation({
    mutationFn: (body: NewEvent) => ok(api.POST("/api/v1/events", { body })),
    onSuccess: refresh,
  });
}

export function useDeleteEvent() {
  const refresh = useRefreshEvents();
  return useMutation({
    mutationFn: async (id: string) => {
      const { error, response } = await api.DELETE(
        "/api/v1/events/{event_id}",
        { params: { path: { event_id: id } } },
      );
      if (!response.ok) throw new ApiRequestError(readApiError(error));
    },
    onSuccess: refresh,
  });
}

export function useLaundry() {
  return useQuery({
    queryKey: ["laundry"],
    queryFn: () => ok(api.GET("/api/v1/laundry")),
  });
}

export function useLaundryDone() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (itemIds: string[]) =>
      ok(api.POST("/api/v1/laundry/done", { body: { item_ids: itemIds } })),
    onSuccess: async (laundry) => {
      queryClient.setQueryData(["laundry"], laundry);
      await Promise.all(
        [["items"], ["item"], ["plan"]].map((queryKey) =>
          queryClient.invalidateQueries({ queryKey }),
        ),
      );
    },
  });
}

export const WEEKDAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

/** The weekday index the API uses: 0 is Monday. */
export function weekdayOf(iso: string): number {
  return (new Date(`${iso}T00:00:00`).getDay() + 6) % 7;
}
