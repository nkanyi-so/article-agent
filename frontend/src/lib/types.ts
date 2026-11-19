/** Names for the API's shapes. The shapes themselves are generated: see `api.gen.ts`. */

import type { components } from "./api.gen";

type Schemas = components["schemas"];

export type ConfigResponse = Schemas["ConfigResponse"];
export type SeedSummary = Schemas["SeedSummary"];
export type RunRow = Schemas["RunRow"];
export type RunDetail = Schemas["RunDetail"];
export type Article = Schemas["Article"];
export type Claim = Schemas["Claim"];
export type RemovedUnit = Schemas["RemovedUnit"];
export type Segment = Schemas["Segment"];
export type StageRecord = Schemas["StageRecord"];
export type StoredModelCall = Schemas["StoredModelCall"];
export type EvalReport = Schemas["EvalReport"];
export type Verdict = Schemas["Verdict"];
export type RunEvent = Schemas["RunEvent"];
export type StageName = StageRecord["name"];

export const STAGES: readonly StageName[] = ["ingest", "extract", "draft", "ground", "evaluate"];
