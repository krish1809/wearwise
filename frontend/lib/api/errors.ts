import type { components } from "@/lib/api/schema";

type ErrorResponse = components["schemas"]["ErrorResponse"];

export type ApiProblem = {
  code: string;
  message: string;
  fields: Record<string, string>;
};

export const NETWORK_ERROR =
  "Can't reach WearWise. Check your connection and try again.";

/** The message and per-field messages from an API error, whatever came back. */
export function readApiError(error: unknown): ApiProblem {
  if (error && typeof error === "object" && "error" in error) {
    const detail = (error as ErrorResponse).error;
    return {
      code: detail.code,
      message: detail.message,
      fields: detail.fields ?? {},
    };
  }
  return {
    code: "unknown",
    message: "Something went wrong. Try again.",
    fields: {},
  };
}

/** Thrown by data hooks so a form can show the API's messages next to its fields. */
export class ApiRequestError extends Error {
  readonly problem: ApiProblem;

  constructor(problem: ApiProblem) {
    super(problem.message);
    this.problem = problem;
  }
}

/** The problem behind a failed request: the API's answer, or a network failure. */
export function problemFrom(error: unknown): ApiProblem {
  if (error instanceof ApiRequestError) return error.problem;
  return { code: "network", message: NETWORK_ERROR, fields: {} };
}
