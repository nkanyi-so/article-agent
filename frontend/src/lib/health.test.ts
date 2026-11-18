import { describe, expect, it } from "vitest";
import { fetchHealth } from "@/lib/health";

function fakeFetch(result: () => Response | Promise<Response>): typeof fetch {
  return async () => result();
}

describe("fetchHealth", () => {
  it("reports mode and version from a healthy backend", async () => {
    const body = JSON.stringify({ status: "ok", mode: "demo", version: "0.1.0" });
    const health = await fetchHealth("https://api.example.com", fakeFetch(() => new Response(body)));

    expect(health).toEqual({ reachable: true, mode: "demo", version: "0.1.0" });
  });

  it("calls the health route of the base it is given", async () => {
    let called = "";
    const spy: typeof fetch = async (input) => {
      called = String(input);
      return new Response("{}");
    };

    await fetchHealth("https://api.example.com", spy);

    expect(called).toBe("https://api.example.com/health");
  });

  it("treats an error status as unreachable", async () => {
    const health = await fetchHealth("x", fakeFetch(() => new Response("no", { status: 503 })));

    expect(health).toEqual({ reachable: false });
  });

  it("treats a body of the wrong shape as unreachable", async () => {
    const health = await fetchHealth("x", fakeFetch(() => new Response('{"status":"ok"}')));

    expect(health).toEqual({ reachable: false });
  });

  it("treats a network or cross-origin failure as unreachable instead of throwing", async () => {
    const health = await fetchHealth(
      "x",
      fakeFetch(() => Promise.reject(new TypeError("Failed to fetch")))
    );

    expect(health).toEqual({ reachable: false });
  });
});
