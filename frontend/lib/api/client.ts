import createClient from "openapi-fetch";

import type { paths } from "@/lib/api/schema";

/**
 * Typed client for the WearWise API. Paths, parameters, and bodies come from the backend's
 * OpenAPI schema; run `make api-types` after changing a route. URLs are relative, so browser
 * requests go to this app, which forwards /api/* to the backend.
 */
export const api = createClient<paths>({ baseUrl: "" });
