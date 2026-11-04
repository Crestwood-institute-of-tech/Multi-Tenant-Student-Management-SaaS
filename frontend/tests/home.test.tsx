import { render, screen } from "@testing-library/react";
import Home from "@/app/page";

describe("Home", () => {
  it("renders the product name", () => {
    render(<Home />);
    expect(
      screen.getByText("Student Management SaaS", { selector: "div" }),
    ).toBeInTheDocument();
  });

  it("renders the call to action", () => {
    render(<Home />);
    expect(screen.getByRole("button", { name: /request a demo/i })).toBeInTheDocument();
  });
});
