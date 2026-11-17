import { getCurrentUser, login, logout } from "@/lib/auth";

describe("authentication API client", () => {
  const fetchMock = jest.fn<ReturnType<typeof fetch>, Parameters<typeof fetch>>();
  const originalFetch = global.fetch;

  beforeEach(() => {
    fetchMock.mockReset();
    global.fetch = fetchMock;
  });

  afterAll(() => {
    global.fetch = originalFetch;
  });

  it("uses credentials and submits a fresh CSRF token for login", async () => {
    fetchMock
      .mockResolvedValueOnce(
        jsonResponse({ csrfToken: "masked-csrf-token" }),
      )
      .mockResolvedValueOnce(
        jsonResponse({ user: { id: "user-uuid", email: "student@example.com" } }),
      );

    await expect(login("student@example.com", "secret")).resolves.toEqual({
      user: { id: "user-uuid", email: "student@example.com" },
    });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      expect.stringMatching(/\/auth\/csrf\/$/),
      expect.objectContaining({ credentials: "include" }),
    );
    const loginRequest = fetchMock.mock.calls[1][1];
    expect(loginRequest?.credentials).toBe("include");
    expect(new Headers(loginRequest?.headers).get("X-CSRFToken")).toBe(
      "masked-csrf-token",
    );
    expect(loginRequest?.body).toBe(
      JSON.stringify({ email: "student@example.com", password: "secret" }),
    );
  });

  it("returns null for the unauthenticated current-user response", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        { detail: "Authentication credentials were not provided." },
        403,
        "Forbidden",
      ),
    );

    await expect(getCurrentUser()).resolves.toBeNull();
  });

  it("submits CSRF proof when logging out", async () => {
    fetchMock
      .mockResolvedValueOnce(
        jsonResponse({ csrfToken: "csrf-token" }),
      )
      .mockResolvedValueOnce(
        jsonResponse({ detail: "Logged out." }),
      );

    await expect(logout()).resolves.toBeUndefined();
    expect(new Headers(fetchMock.mock.calls[1][1]?.headers).get("X-CSRFToken")).toBe(
      "csrf-token",
    );
  });

  it("does not suppress non-authentication failures while fetching the user", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ detail: "Unavailable." }, 503, "Service Unavailable"),
    );

    await expect(getCurrentUser()).rejects.toMatchObject({ status: 503 });
  });
});

function jsonResponse(body: unknown, status = 200, statusText = "OK"): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText,
    json: async () => body,
  } as Response;
}
