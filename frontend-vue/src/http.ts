import axios from "axios";

/**
 * M-3: configurable HTTP timeout for the generated API client.
 *
 * The generated client (`src/api/core/request.ts`) calls `axios.request(...)`
 * without a `timeout`, so a backend that accepts the connection but never
 * answers would leave every request — and the loading state that awaits it —
 * pending forever. This module is deliberately *not* generated, so running
 * `npm run generate-api` never overwrites it.
 *
 * The timeout is applied to the shared `axios` default instance, which is the
 * instance the generated client uses.
 */

export const DEFAULT_TIMEOUT_MS = 15_000;

/**
 * Read a timeout in milliseconds from a raw environment value.
 *
 * Falls back to {@link DEFAULT_TIMEOUT_MS} for a missing or malformed value
 * and warns, so a typo in `VITE_API_TIMEOUT_MS` is visible in the browser
 * console instead of silently changing request behaviour.
 */
export const parseTimeoutMs = (raw: unknown): number => {
  if (typeof raw !== "string" || raw.trim() === "") {
    return DEFAULT_TIMEOUT_MS;
  }

  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    console.warn(
      `[http] VITE_API_TIMEOUT_MS="${raw}" is not a positive number; ` +
        `using ${DEFAULT_TIMEOUT_MS} ms instead.`,
    );
    return DEFAULT_TIMEOUT_MS;
  }

  return parsed;
};

export const API_TIMEOUT_MS = parseTimeoutMs(
  import.meta.env?.VITE_API_TIMEOUT_MS,
);

/**
 * Apply the configured timeout to the axios instance used by the generated
 * API client. Call this once, before the app is mounted.
 */
export const configureHttpClient = (): void => {
  axios.defaults.timeout = API_TIMEOUT_MS;
};
