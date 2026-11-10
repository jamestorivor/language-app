import { API_BASE_URL } from "./config";
import { loggedFetch } from "./client";
import type {
  CreateEpisodeRequest,
  EpisodeResponse,
  SegmentResponse,
  PodcastLanguage,
} from "../contracts/podcast";

const API_PREFIX = "podcasts";

async function createEpisode(
  episode: CreateEpisodeRequest,
): Promise<EpisodeResponse> {
  const url = new URL(API_PREFIX, API_BASE_URL);
  return await loggedFetch("podcast.create", url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(episode),
  }).then(async (response) => {
    if (!response.ok) {
      const body: unknown = await response.json().catch(() => null);
      const detail = body && typeof body === "object" && "detail" in body ? body.detail : null;
      throw new Error(typeof detail === "string" ? detail : `Backend response ${response.status}`);
    }
    return response.json();
  });
}

async function getEpisodes(): Promise<EpisodeResponse[]> {
  const url = new URL(API_PREFIX, API_BASE_URL);
  return await loggedFetch("podcast.list", url).then((response) => {
    if (!response.ok) {
      throw new Error(`Backend response ${response.status}`);
    }
    return response.json();
  });
}

async function getEpisodeById(episode_id: number): Promise<EpisodeResponse> {
  const url = new URL(`${API_PREFIX}/${episode_id}`, API_BASE_URL);
  return await loggedFetch("podcast.getEpisode", url).then((response) => {
    if (!response.ok) {
      throw new Error(`Backend response ${response.status}`);
    }
    return response.json();
  });
}

async function updateEpisode(episodeId: number, details: { title: string; author: string; language: PodcastLanguage }): Promise<EpisodeResponse> {
  const response = await loggedFetch("podcast.update", new URL(`${API_PREFIX}/${episodeId}`, API_BASE_URL), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(details),
  });
  if (!response.ok) throw new Error(`Could not save changes (response ${response.status}).`);
  return response.json();
}

async function deleteEpisode(episodeId: number): Promise<void> {
  const response = await loggedFetch("podcast.delete", new URL(`${API_PREFIX}/${episodeId}`, API_BASE_URL), {
    method: "DELETE",
  });
  if (!response.ok) throw new Error(`Could not delete podcast (response ${response.status}).`);
}

async function getSegments(episode_id: number): Promise<SegmentResponse[]> {
  const chunk_path = `${episode_id}/chunks`;
  const url = new URL(`${API_PREFIX}/${chunk_path}`, API_BASE_URL);
  return await loggedFetch("podcast.listSegments", url).then((response) => {
    if (!response.ok) {
      throw new Error(`Backend response ${response.status}`);
    }
    return response.json();
  });
}

async function getSegmentById(segment_id: number): Promise<SegmentResponse> {
  const chunk_path = `chunks/${segment_id}`;
  const url = new URL(`${API_PREFIX}/${chunk_path}`, API_BASE_URL);
  return await loggedFetch("podcast.getSegment", url).then((response) => {
    if (!response.ok) {
      throw new Error(`Backend response ${response.status}`);
    }
    return response.json();
  });
}

export {
  getEpisodes,
  createEpisode,
  getSegments,
  getEpisodeById,
  getSegmentById,
  updateEpisode,
  deleteEpisode,
};
