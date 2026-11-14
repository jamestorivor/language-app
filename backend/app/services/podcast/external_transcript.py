"""Turn an uploaded text transcript into snippets with episode offsets."""
import re

from fastapi import HTTPException


_TIMESTAMP = re.compile(r"^\s*(?:\[(\d+:\d{2}(?::\d{2})?(?:\.\d+)?)\]|(\d+:\d{2}(?::\d{2})?(?:\.\d+)?))\s+(.+?)\s*$")


def parse_external_transcript(text: str, duration: float) -> list[dict]:
    text = text.lstrip("\ufeff").strip()
    if not text:
        raise HTTPException(status_code=422, detail="The transcript file is empty.")
    lines = [line for line in text.splitlines() if line.strip()]
    if not _TIMESTAMP.match(lines[0]):
        return [{"start": 0, "text": text}]

    snippets = []
    for line in lines:
        match = _TIMESTAMP.match(line)
        if not match:
            raise HTTPException(status_code=422, detail="Each line in a timestamped transcript must start with a timestamp and contain text.")
        parts = (match.group(1) or match.group(2)).split(":")
        if float(parts[-1]) >= 60 or (len(parts) == 3 and int(parts[-2]) >= 60):
            raise HTTPException(status_code=422, detail="A transcript timestamp is invalid.")
        start = sum(float(part) * 60 ** index for index, part in enumerate(reversed(parts)))
        if start >= duration:
            raise HTTPException(status_code=422, detail="A transcript timestamp is outside the podcast duration.")
        snippets.append({"start": start, "text": match.group(3)})
    return snippets
