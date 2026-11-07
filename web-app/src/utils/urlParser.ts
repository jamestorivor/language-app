export type PodcastLink =
  | { provider: "spotify"; id: string }
  | { provider: "youtube"; id: string };

function parsePodcastLink(input: string): PodcastLink | null {
  let url: URL;

  try {
    url = new URL(input);
  } catch {
    return null;
  }

  if (url.protocol !== "https:") return null;

  if (url.hostname === "open.spotify.com") {
    const match = url.pathname.match(/^\/episode\/([a-zA-Z0-9]+)\/?$/);
    return match ? { provider: "spotify", id: match[1] } : null;
  }

  if (url.hostname === "www.youtube.com" || url.hostname === "youtube.com") {
    const id = url.pathname === "/watch" ? url.searchParams.get("v") : null;
    return id && /^[a-zA-Z0-9_-]{11}$/.test(id)
      ? { provider: "youtube", id }
      : null;
  }

  if (url.hostname === "youtu.be") {
    const id = url.pathname.slice(1);
    return /^[a-zA-Z0-9_-]{11}$/.test(id) ? { provider: "youtube", id } : null;
  }

  return null;
}

export default parsePodcastLink;
