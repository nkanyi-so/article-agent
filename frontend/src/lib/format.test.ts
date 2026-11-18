import { describe, expect, it } from "vitest";
import { formatDuration, totalDuration, truncate } from "@/lib/format";

describe("formatDuration", () => {
  it("keeps sub-second durations in milliseconds", () => {
    expect(formatDuration(250)).toBe("250ms");
  });

  it("shows seconds to two places under a minute", () => {
    expect(formatDuration(1840)).toBe("1.84s");
  });

  it("splits a minute or more into minutes and seconds", () => {
    expect(formatDuration(65000)).toBe("1m 5s");
  });
});

describe("totalDuration", () => {
  it("sums stage durations", () => {
    expect(totalDuration([{ duration_ms: 120 }, { duration_ms: 380 }])).toBe(500);
  });
});

describe("truncate", () => {
  it("leaves a short string alone and marks a cut one", () => {
    expect(truncate("short", 10)).toBe("short");
    expect(truncate("a longer string", 8)).toBe("a longer…");
  });
});
