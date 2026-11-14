"""Turn an uploaded text transcript into snippets with episode offsets."""
import re

from fastapi import HTTPException


_TIMESTAMP = re.compile(r"^\s*(?:\[(\d+:\d{2}(?::\d{2})?(?:\.\d+)?)\]|(\d+:\d{2}(?::\d{2})?(?:\.\d+)?))\s+(.+?)\s*$")


def parse_external_transcript(text: str, duration: float, *, require_timestamps: bool = False, file_format: str = "txt") -> list[dict]:
    text = text.lstrip("\ufeff").strip()
    if not text:
        raise HTTPException(status_code=422, detail="The transcript file is empty.")
    if file_format in {"srt", "vtt"}:
        return _parse_subtitles(text, duration, file_format)
    lines = [line for line in text.splitlines() if line.strip()]
    if not _TIMESTAMP.match(lines[0]):
        if require_timestamps:
            raise HTTPException(status_code=422, detail="Each transcript line needs a timestamp to update segment times.")
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


_CUE_TIMING = re.compile(
    r"^\s*(\d{2,}:\d{2}(?::\d{2})?[.,]\d{3})\s+-->\s+"
    r"(\d{2,}:\d{2}(?::\d{2})?[.,]\d{3})(?:\s+.*)?\s*$"
)
_CUE_TAG = re.compile(r"</?(?:b|i|u|s|c(?:\.[^\s>]*)?|v(?:\s+[^>]*)?|lang(?:\s+[^>]*)?|ruby|rt|font(?:\s+[^>]*)?)\s*>|<\d{2,}:\d{2}(?::\d{2})?\.\d{3}>", re.IGNORECASE)


def _cue_seconds(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    if float(parts[-1]) >= 60 or (len(parts) == 3 and int(parts[-2]) >= 60):
        raise HTTPException(status_code=422, detail="A subtitle timestamp is invalid.")
    return sum(float(part) * 60 ** index for index, part in enumerate(reversed(parts)))


def _parse_subtitles(text: str, duration: float, file_format: str) -> list[dict]:
    from html import unescape

    lines = text.splitlines()
    if file_format == "vtt":
        if not lines or not re.fullmatch(r"WEBVTT(?:[ \t].*)?", lines[0]):
            raise HTTPException(status_code=422, detail="The VTT file must start with WEBVTT.")
        lines = lines[1:]
        # WebVTT header metadata precedes the first blank line.
        while lines and lines[0].strip():
            lines.pop(0)

    blocks = re.split(r"\n[ \t]*\n", "\n".join(lines).strip())
    snippets = []
    for block in blocks:
        cue = block.splitlines()
        if not cue or not cue[0].strip():
            continue
        if file_format == "vtt" and re.match(r"^(?:NOTE(?:\s|$)|STYLE\s*$|REGION\s*$)", cue[0]):
            continue
        timing_index = 0 if _CUE_TIMING.match(cue[0]) else 1
        if timing_index >= len(cue) or (file_format == "srt" and timing_index and not cue[0].strip().isdigit()):
            raise HTTPException(status_code=422, detail="The subtitle file contains an invalid cue.")
        match = _CUE_TIMING.match(cue[timing_index])
        if not match:
            raise HTTPException(status_code=422, detail="The subtitle file contains an invalid cue timestamp.")
        start, end = (_cue_seconds(value) for value in match.groups())
        if end <= start:
            raise HTTPException(status_code=422, detail="A subtitle cue must end after it starts.")
        if start >= duration:
            raise HTTPException(status_code=422, detail="A subtitle timestamp is outside the podcast duration.")
        cue_text = unescape(_CUE_TAG.sub("", "\n".join(cue[timing_index + 1:]))).strip()
        if not cue_text:
            raise HTTPException(status_code=422, detail="A subtitle cue has no text.")
        snippets.append({"start": start, "text": cue_text})
    if not snippets:
        raise HTTPException(status_code=422, detail="The subtitle file has no cues.")
    return snippets
