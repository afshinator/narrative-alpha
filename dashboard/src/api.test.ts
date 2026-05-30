import { describe, it, expect, vi } from "vitest";

describe("fetchReports", () => {
  it("calls /api/reports and returns cluster list", async () => {
    const fake = [{ cluster_id: "EVT-001", search_query: "test", industry_vertical: "TECH", timestamp_utc: "now", corpus_count: 5, corpus_capped: false }];
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(fake) } as Response);
    const { fetchReports } = await import("./api");
    const result = await fetchReports();
    expect(result).toEqual(fake);
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/reports");
  });

  it("includes response body detail in error message", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false, status: 422, statusText: "Unprocessable Entity",
      json: () => Promise.resolve({ detail: "Missing required field: model" }),
    } as Response);
    const { fetchConfig } = await import("./api");
    await expect(fetchConfig()).rejects.toThrow("GET /api/config failed (422): Missing required field: model");
  });

  it("falls back to statusText when response body is not JSON", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false, status: 500, statusText: "Internal Server Error",
      json: () => Promise.reject(new Error("not JSON")),
    } as Response);
    const { fetchReports } = await import("./api");
    await expect(fetchReports()).rejects.toThrow("GET /api/reports failed (500): Internal Server Error");
  });
});

describe("fetchReport", () => {
  it("calls /api/reports/{id}", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ event_meta: { cluster_id: "EVT-001" } }) } as Response);
    const { fetchReport } = await import("./api");
    await fetchReport("EVT-001");
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/reports/EVT-001");
  });
});

describe("saveConfig", () => {
  it("POSTs config to /api/config", async () => {
    const config = { call_1_entity_normalization: { provider: "deepseek", model: "v4", thinking: false, temperature: 0.1 } } as any;
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ status: "ok", config }) } as Response);
    const { saveConfig } = await import("./api");
    await saveConfig(config);
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/config", expect.objectContaining({ method: "POST" }));
  });
});

describe("submitPipeline", () => {
  it("POSTs keyword and vertical", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ event_meta: {} }) } as Response);
    const { submitPipeline } = await import("./api");
    await submitPipeline("test", "TECH");
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/pipeline", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ keyword: "test", vertical: "TECH" }),
    }));
  });
});

describe("fetchEnvHealth", () => {
  it("calls /api/health/env and returns env health object", async () => {
    const fake = { status: "ok", detail: "All required vars set", present: ["DEEPSEEK_API_KEY"], missing: [] };
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(fake) } as Response);
    const { fetchEnvHealth } = await import("./api");
    const result = await fetchEnvHealth();
    expect(result).toEqual(fake);
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/health/env");
  });

  it("throws on non-ok response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false, status: 500, statusText: "Internal Server Error",
      json: () => Promise.reject(new Error("not JSON")),
    } as Response);
    const { fetchEnvHealth } = await import("./api");
    await expect(fetchEnvHealth()).rejects.toThrow("GET /api/health/env failed (500): Internal Server Error");
  });
});

describe("streamPipeline", () => {
  it("constructs EventSource with correct URL", async () => {
    const fakeEs = { onmessage: null, onerror: null } as unknown as EventSource;
    const MockEs = vi.fn(() => fakeEs);
    vi.stubGlobal("EventSource", MockEs);
    const { streamPipeline } = await import("./api");
    streamPipeline("ai regulation", "TECHNOLOGY", vi.fn(), vi.fn());
    expect(MockEs).toHaveBeenCalledWith(
      "/api/pipeline/stream?keyword=ai+regulation&vertical=TECHNOLOGY"
    );
    vi.unstubAllGlobals();
  });

  it("calls onEvent with parsed JSON when message arrives", async () => {
    const fakeEs: any = { onmessage: null, onerror: null };
    vi.stubGlobal("EventSource", vi.fn(() => fakeEs));
    const onEvent = vi.fn();
    const { streamPipeline } = await import("./api");
    streamPipeline("test", "TECHNOLOGY", onEvent, vi.fn());
    fakeEs.onmessage({ data: '{"step":"discovering","message":"Searching..."}' });
    expect(onEvent).toHaveBeenCalledWith({ step: "discovering", message: "Searching..." });
    vi.unstubAllGlobals();
  });

  it("returns the EventSource so the caller can close it", async () => {
    const fakeEs = { onmessage: null, onerror: null };
    vi.stubGlobal("EventSource", vi.fn(() => fakeEs));
    const { streamPipeline } = await import("./api");
    const es = streamPipeline("test", "TECHNOLOGY", vi.fn(), vi.fn());
    expect(es).toBe(fakeEs);
    vi.unstubAllGlobals();
  });
});
