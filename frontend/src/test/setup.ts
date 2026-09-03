import "@testing-library/jest-dom/vitest";


import { vi } from "vitest";

vi.mock("react-plotly.js", () => ({ default: () => null }));
