import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { ApiRequestError, readApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

export type Place = components["schemas"]["PlaceOut"];
export type DayWeather = components["schemas"]["DayWeatherOut"];
export type WeatherSummary = {
  source: "forecast" | "manual" | "season";
  feels_like: number | null;
  rain_chance: number | null;
};

/** Places matching a name, most likely first. */
export async function searchPlaces(query: string): Promise<Place[]> {
  const { data, error } = await api.GET("/api/v1/places", {
    params: { query: { q: query } },
  });
  if (data !== undefined) return data;
  throw new ApiRequestError(readApiError(error));
}

/** The weather for the next few days, from the profile's city or the manual setting. */
export function useWeather(days = 1) {
  return useQuery({
    queryKey: ["weather", days],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/weather", {
        params: { query: { days } },
      });
      if (data !== undefined) return data;
      throw new ApiRequestError(readApiError(error));
    },
    staleTime: 30 * 60_000,
  });
}

/** "Feels like 31°, 20% chance of rain", or what the plan goes by when there's no forecast. */
export function weatherLine(weather: WeatherSummary): string {
  if (weather.feels_like === null) return "No forecast: going by the season";
  const temperature = `Feels like ${Math.round(weather.feels_like)}°`;
  const rain =
    weather.rain_chance === null
      ? ""
      : `, ${weather.rain_chance}% chance of rain`;
  return `${temperature}${rain}`;
}

/** Where the weather came from, in a few words. */
export function weatherSource(weather: WeatherSummary): string {
  return weather.source === "forecast"
    ? "Forecast"
    : weather.source === "manual"
      ? "Your setting"
      : "By season";
}

export const MANUAL_WEATHER = [
  { id: "hot", label: "Hot" },
  { id: "mild", label: "Mild" },
  { id: "cold", label: "Cold" },
  { id: "rainy", label: "Rainy" },
] as const;
