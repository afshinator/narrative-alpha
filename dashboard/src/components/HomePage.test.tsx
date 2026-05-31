import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { HomePage } from "./HomePage";

vi.mock("./PipelineRunner", () => ({
	PipelineRunner: () => <div data-testid="pipeline-runner-stub" />,
}));

beforeEach(() => {
	vi.restoreAllMocks();
});

it("shows loading state initially", () => {
	vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
	render(
		<MemoryRouter>
			<HomePage />
		</MemoryRouter>,
	);
	expect(screen.getByText("Loading reports…")).toBeTruthy();
});

it("shows error message on fetch failure", async () => {
	vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(
		new Error("Network error"),
	);
	render(
		<MemoryRouter>
			<HomePage />
		</MemoryRouter>,
	);
	expect(await screen.findByText(/Backend unreachable/)).toBeTruthy();
});

it("shows empty state when no reports", async () => {
	vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
		ok: true,
		json: () => Promise.resolve([]),
	} as Response);
	render(
		<MemoryRouter>
			<HomePage />
		</MemoryRouter>,
	);
	expect(await screen.findByText(/No reports yet/)).toBeTruthy();
});

it("renders report cards from fetch", async () => {
	const fake = [
		{
			cluster_id: "EVT-001",
			search_query: "Test query",
			industry_vertical: "TECH",
			timestamp_utc: "2026-05-30T00:00:00Z",
			corpus_count: 5,
			corpus_capped: false,
		},
	];
	vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
		ok: true,
		json: () => Promise.resolve(fake),
	} as Response);
	render(
		<MemoryRouter>
			<HomePage />
		</MemoryRouter>,
	);
	expect(await screen.findByText("Test query")).toBeTruthy();
	expect(screen.getByText(/5 articles/)).toBeTruthy();
});
