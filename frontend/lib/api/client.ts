import createClient, { type Middleware } from "openapi-fetch";

import type { paths } from "@/lib/api/schema";
import { newRequestId } from "@/lib/report-error";

/**
 * Typed client for the WearWise API. Paths, parameters, and bodies come from the backend's
 * OpenAPI schema; run `make api-types` after changing a route. URLs are relative, so browser
 * requests go to this app, which forwards /api/* to the backend.
 */
export const api = createClient<paths>({
  baseUrl: "",
  // The API refuses state-changing requests without this header; other sites can't add it,
  // which blocks forged requests (CSRF).
  headers: { "X-Requested-With": "fetch" },
});

// Each request carries an id the server logs; an error the server returns quotes it.
export const requestIds: Middleware = {
  onRequest({ request }) {
    request.headers.set("X-Request-ID", newRequestId());
    return request;
  },
};
api.use(requestIds);
