// M-3: the generated API client must not be able to hang forever.
//
// Run with `npm test` (Node's built-in test runner; no extra dependency).
// Node executes these .ts files directly by stripping the type annotations.

import assert from "node:assert/strict";
import http from "node:http";
import test from "node:test";

import axios from "axios";

import {
  API_TIMEOUT_MS,
  DEFAULT_TIMEOUT_MS,
  configureHttpClient,
  parseTimeoutMs,
} from "../src/http.ts";

test("missing or malformed timeout falls back to the default", () => {
  assert.equal(parseTimeoutMs(undefined), DEFAULT_TIMEOUT_MS);
  assert.equal(parseTimeoutMs(""), DEFAULT_TIMEOUT_MS);
  assert.equal(parseTimeoutMs("   "), DEFAULT_TIMEOUT_MS);
  assert.equal(parseTimeoutMs("abc"), DEFAULT_TIMEOUT_MS);
  assert.equal(parseTimeoutMs("0"), DEFAULT_TIMEOUT_MS);
  assert.equal(parseTimeoutMs("-1"), DEFAULT_TIMEOUT_MS);
  assert.equal(parseTimeoutMs("Infinity"), DEFAULT_TIMEOUT_MS);
});

test("a positive numeric timeout is honoured", () => {
  assert.equal(parseTimeoutMs("5000"), 5000);
  assert.equal(parseTimeoutMs("12000"), 12000);
});

test("configureHttpClient applies the timeout to the client the generated code uses", () => {
  axios.defaults.timeout = undefined as unknown as number;

  configureHttpClient();

  // src/api/core/request.ts calls `axios.request(...)` (the default instance)
  // without a timeout, so the axios default is what protects it.
  assert.equal(axios.defaults.timeout, API_TIMEOUT_MS);
});

test("an axios default timeout aborts a request the server never answers", async () => {
  const server = http.createServer(() => {
    // Deliberately never respond: this is the hang M-3 protects against.
  });

  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  assert.ok(address && typeof address === "object");

  const previousTimeout = axios.defaults.timeout;
  axios.defaults.timeout = 150;

  try {
    await assert.rejects(
      axios.get(`http://127.0.0.1:${address.port}/hang`),
      (error: { code?: string }) => error.code === "ECONNABORTED",
    );
  } finally {
    axios.defaults.timeout = previousTimeout;
    await new Promise<void>((resolve) => server.close(() => resolve()));
  }
});
