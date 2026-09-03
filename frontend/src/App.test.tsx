import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("renders the analytics workspace", () => {
    render(<App />);
    expect(screen.getByText("DataPilot")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/问一个关于数据的问题/)).toBeInTheDocument();
  });
});
