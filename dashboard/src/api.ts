import type {
	ForensicReport,
	ClusterSummary,
	LLMConfig,
	PipelineEvent,
	EnvHealth,
} from "./types";

const BASE = "/api";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
	const args: [string, RequestInit?] = init ? [url, init] : [url];
	let res: Response;
	try {
		res = await fetch(...args);
	} catch {
		const method = init?.method ?? "GET";
		throw new Error(
			`Backend unreachable (${method} ${url}). Ensure the server is running on port 3001.`,
		);
	}
	if (!res.ok) {
		let detail = res.statusText;
		try {
			const body = await res.json();
			detail = body.detail ?? JSON.stringify(body);
		} catch {
			// response body wasn't JSON, keep statusText
		}
		const method = init?.method ?? "GET";
		throw new Error(`${method} ${url} failed (${res.status}): ${detail}`);
	}
	return res.json() as Promise<T>;
}

export function fetchReports(): Promise<ClusterSummary[]> {
	return fetchJson<ClusterSummary[]>(`${BASE}/reports`);
}

export function fetchReport(clusterId: string): Promise<ForensicReport> {
	return fetchJson<ForensicReport>(
		`${BASE}/reports/${encodeURIComponent(clusterId)}`,
	);
}

export function fetchConfig(): Promise<LLMConfig> {
	return fetchJson<LLMConfig>(`${BASE}/config`);
}

export function saveConfig(
	config: LLMConfig,
): Promise<{ status: string; config: LLMConfig }> {
	return fetchJson(`${BASE}/config`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(config),
	});
}

export function fetchEnvHealth(): Promise<EnvHealth> {
	return fetchJson<EnvHealth>(`${BASE}/health/env`);
}

export function submitPipeline(
	keyword: string,
	vertical: string,
): Promise<ForensicReport> {
	return fetchJson(`${BASE}/pipeline`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ keyword, vertical }),
	});
}

export function streamPipeline(
	keyword: string,
	vertical: string,
	onEvent: (e: PipelineEvent) => void,
	onError: (err: Event) => void,
): EventSource {
	const params = new URLSearchParams({ keyword, vertical });
	const es = new EventSource(`${BASE}/pipeline/stream?${params.toString()}`);
	es.onmessage = (msg: MessageEvent) => {
		try {
			onEvent(JSON.parse(msg.data) as PipelineEvent);
		} catch {
			// malformed event — ignore
		}
	};
	es.onerror = onError;
	return es;
}
