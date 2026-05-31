import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { PipelineRunner } from "./PipelineRunner";

vi.mock("../api", async (importOriginal) => {
	const actual = await importOriginal<typeof import("../api")>();
	return { ...actual, streamPipeline: vi.fn() };
});

import { streamPipeline } from "../api";

beforeEach(() => {
	vi.clearAllMocks();
});

function renderRunner(onComplete?: () => void) {
	return render(
		<MemoryRouter>
			<PipelineRunner onComplete={onComplete} />
		</MemoryRouter>,
	);
}

describe("PipelineRunner — idle", () => {
	it("renders keyword input, vertical selector, and submit button", () => {
		renderRunner();
		expect(screen.getByPlaceholderText(/Enter keyword/i)).toBeTruthy();
		expect(screen.getByRole("combobox")).toBeTruthy();
		expect(screen.getByRole("button", { name: /Run Pipeline/i })).toBeTruthy();
	});

	it("disables submit when keyword is empty", () => {
		renderRunner();
		const btn = screen.getByRole("button", {
			name: /Run Pipeline/i,
		}) as HTMLButtonElement;
		expect(btn.disabled).toBe(true);
	});

	it("enables submit when keyword is typed", () => {
		renderRunner();
		fireEvent.change(screen.getByPlaceholderText(/Enter keyword/i), {
			target: { value: "AI regulation" },
		});
		const btn = screen.getByRole("button", {
			name: /Run Pipeline/i,
		}) as HTMLButtonElement;
		expect(btn.disabled).toBe(false);
	});
});

describe("PipelineRunner — running", () => {
	it("calls streamPipeline with keyword and vertical on submit", () => {
		vi.mocked(streamPipeline).mockReturnValue({
			close: vi.fn(),
		} as unknown as EventSource);
		renderRunner();
		fireEvent.change(screen.getByPlaceholderText(/Enter keyword/i), {
			target: { value: "ai" },
		});
		fireEvent.click(screen.getByRole("button", { name: /Run Pipeline/i }));
		expect(streamPipeline).toHaveBeenCalledWith(
			"ai",
			"TECHNOLOGY",
			expect.any(Function),
			expect.any(Function),
		);
	});

	it("shows Running… and disables inputs during run", () => {
		vi.mocked(streamPipeline).mockReturnValue({
			close: vi.fn(),
		} as unknown as EventSource);
		renderRunner();
		fireEvent.change(screen.getByPlaceholderText(/Enter keyword/i), {
			target: { value: "ai" },
		});
		fireEvent.click(screen.getByRole("button", { name: /Run Pipeline/i }));
		expect(screen.getByRole("button", { name: /Running/i })).toBeTruthy();
		expect(
			(screen.getByPlaceholderText(/Enter keyword/i) as HTMLInputElement)
				.disabled,
		).toBe(true);
	});

	it("renders progress steps as events arrive", () => {
		let capturedOnEvent: ((e: any) => void) | null = null;
		vi.mocked(streamPipeline).mockImplementation((_kw, _v, onEvent) => {
			capturedOnEvent = onEvent;
			return { close: vi.fn() } as unknown as EventSource;
		});
		renderRunner();
		fireEvent.change(screen.getByPlaceholderText(/Enter keyword/i), {
			target: { value: "ai" },
		});
		fireEvent.click(screen.getByRole("button", { name: /Run Pipeline/i }));
		act(() => {
			capturedOnEvent!({ step: "discovering", message: "Searching..." });
		});
		expect(screen.getByText(/Discovering articles/i)).toBeTruthy();
		act(() => {
			capturedOnEvent!({ step: "ingesting", message: "Fetching..." });
		});
		expect(screen.getByText(/Ingesting content/i)).toBeTruthy();
	});

	it("accumulates per-article ingest results in a list", () => {
		let capturedOnEvent: ((e: any) => void) | null = null;
		vi.mocked(streamPipeline).mockImplementation((_kw, _v, onEvent) => {
			capturedOnEvent = onEvent;
			return { close: vi.fn() } as unknown as EventSource;
		});
		renderRunner();
		fireEvent.change(screen.getByPlaceholderText(/Enter keyword/i), {
			target: { value: "ai" },
		});
		fireEvent.click(screen.getByRole("button", { name: /Run Pipeline/i }));
		act(() => {
			capturedOnEvent!({
				step: "ingesting",
				message: "Reuters",
				detail: { source_name: "Reuters", domain: "reuters.com", status: "ok" },
			});
		});
		act(() => {
			capturedOnEvent!({
				step: "ingesting",
				message: "BBC",
				detail: { source_name: "BBC", domain: "bbc.com", status: "ok" },
			});
		});
		// Only one row for "ingesting" phase label
		const ingestingLabels = screen.getAllByText(/Ingesting content/i);
		expect(ingestingLabels).toHaveLength(1);
		// Both articles visible in accumulative list
		expect(screen.getByText("Reuters")).toBeTruthy();
		expect(screen.getByText("BBC")).toBeTruthy();
		// Phase message shows count
		expect(screen.getByText(/Processed 2 articles/i)).toBeTruthy();
	});
});

describe("PipelineRunner — error", () => {
	it("shows error detail from error event", () => {
		let capturedOnEvent: ((e: any) => void) | null = null;
		vi.mocked(streamPipeline).mockImplementation((_kw, _v, onEvent) => {
			capturedOnEvent = onEvent;
			return { close: vi.fn() } as unknown as EventSource;
		});
		renderRunner();
		fireEvent.change(screen.getByPlaceholderText(/Enter keyword/i), {
			target: { value: "ai" },
		});
		fireEvent.click(screen.getByRole("button", { name: /Run Pipeline/i }));
		act(() => {
			capturedOnEvent!({
				step: "error",
				message: "Pipeline failed",
				detail: "BrightData timeout",
			});
		});
		expect(screen.getByText(/BrightData timeout/i)).toBeTruthy();
	});

	it("shows connection lost on onerror", () => {
		let capturedOnError: ((e: Event) => void) | null = null;
		vi.mocked(streamPipeline).mockImplementation(
			(_kw, _v, _onEvent, onError) => {
				capturedOnError = onError;
				return { close: vi.fn() } as unknown as EventSource;
			},
		);
		renderRunner();
		fireEvent.change(screen.getByPlaceholderText(/Enter keyword/i), {
			target: { value: "ai" },
		});
		fireEvent.click(screen.getByRole("button", { name: /Run Pipeline/i }));
		act(() => {
			capturedOnError!(new Event("error"));
		});
		expect(screen.getByText(/Connection to server lost/i)).toBeTruthy();
	});
});

describe("PipelineRunner — sub-step messages", () => {
	it("updates phase message as analyzing events arrive", () => {
		let capturedOnEvent: ((e: any) => void) | null = null;
		vi.mocked(streamPipeline).mockImplementation((_kw, _v, onEvent) => {
			capturedOnEvent = onEvent;
			return { close: vi.fn() } as unknown as EventSource;
		});
		renderRunner();
		fireEvent.change(screen.getByPlaceholderText(/Enter keyword/i), {
			target: { value: "ai" },
		});
		fireEvent.click(screen.getByRole("button", { name: /Run Pipeline/i }));
		// Prime the analyzing phase
		act(() => {
			capturedOnEvent!({
				step: "analyzing",
				message: "Registering outlets...",
			});
		});
		expect(screen.getByText(/Registering outlets/)).toBeTruthy();
		// Update message
		act(() => {
			capturedOnEvent!({
				step: "analyzing",
				message: "Normalizing entities (LLM 1/4)...",
			});
		});
		expect(screen.getByText(/Normalizing entities/)).toBeTruthy();
		// Earlier message replaced
		expect(screen.queryByText(/Registering outlets/)).toBeNull();
	});

	it("updates synthesizing message from event", () => {
		let capturedOnEvent: ((e: any) => void) | null = null;
		vi.mocked(streamPipeline).mockImplementation((_kw, _v, onEvent) => {
			capturedOnEvent = onEvent;
			return { close: vi.fn() } as unknown as EventSource;
		});
		renderRunner();
		fireEvent.change(screen.getByPlaceholderText(/Enter keyword/i), {
			target: { value: "ai" },
		});
		fireEvent.click(screen.getByRole("button", { name: /Run Pipeline/i }));
		act(() => {
			capturedOnEvent!({
				step: "synthesizing",
				message: "Generating forensic report...",
			});
		});
		expect(screen.getByText(/Generating forensic report/)).toBeTruthy();
	});
});
