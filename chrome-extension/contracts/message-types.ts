import type { UpdateFamiliarityScoreResponse } from "./jap-vocab";
import type { TokenGroup } from "./parse-japanese";

type MessageLayerResponse<T> =
  | { ok: true; response: T }
  | { ok: false; error: string };

export type { MessageLayerResponse };
