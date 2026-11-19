import { describe, expect, it } from "vitest";
import { myRuns, rememberRun, type MyRun } from "./my-runs";

function store(initial?: string) {
  const data = new Map<string, string>(initial === undefined ? [] : [["article-agent.runs", initial]]);
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => void data.set(key, value),
  };
}
const run = (id: string, kind: MyRun["kind"] = "run"): MyRun => ({
  id,
  title: "Quillmoor Books: interview with the founder",
  kind,
  at: "2026-11-19T10:00:00Z",
});

describe("the runs this browser started", () => {
  it("are listed newest first, and a run remembered twice is listed once", () => {
    const s = store();
    rememberRun(run("s--quillmoor-books--0a1b2c3d"), s);
    rememberRun(run("s--quillmoor-books--0a1b2c3d--r-draft--11111111", "re-run"), s);
    rememberRun(run("s--quillmoor-books--0a1b2c3d"), s);
    expect(myRuns(s).map((r) => [r.id, r.kind])).toEqual([
      ["s--quillmoor-books--0a1b2c3d", "run"],
      ["s--quillmoor-books--0a1b2c3d--r-draft--11111111", "re-run"],
    ]);
  });

  it("keep the twelve newest", () => {
    const s = store();
    for (let n = 0; n < 15; n++) rememberRun(run(`s--quillmoor-books--000000${String(n).padStart(2, "0")}`), s);
    expect(myRuns(s)).toHaveLength(12);
    expect(myRuns(s)[0]?.id).toBe("s--quillmoor-books--00000014");
  });

  it("ignore anything in storage that this code did not write", () => {
    expect(myRuns(store("not json"))).toEqual([]);
    expect(myRuns(store('{"id":"x"}'))).toEqual([]);
    const mixed = JSON.stringify([run("good-one"), { id: "../../etc", title: "t", kind: "run", at: "" }, { id: 7 }, null]);
    expect(myRuns(store(mixed)).map((r) => r.id)).toEqual(["good-one"]);
  });

  it("are simply empty when the browser has no storage", () => {
    expect(myRuns(null)).toEqual([]);
    expect(() => rememberRun(run("a"), null)).not.toThrow();
  });
});
