#!/usr/bin/env python3
"""Check SRT structure and time bounds, without claiming audio alignment."""
import argparse
import json
from pathlib import Path
import re
import sys


STAMP = r"(\d{2,}):([0-5]\d):([0-5]\d),(\d{3})"
RANGE = re.compile(r"^" + STAMP + r"\s*-->\s*" + STAMP + r"$")


def seconds(groups):
    hours, minutes, secs, millis = map(int, groups)
    return hours * 3600 + minutes * 60 + secs + millis / 1000


def validate(text, duration=None):
    errors, warnings = [], []
    normalized = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").strip()
    blocks = re.split(r"\n[ \t]*\n", normalized) if normalized else []
    previous_start, previous_end = -1.0, -1.0
    last_end, cue_count = 0.0, 0
    if not blocks:
        errors.append({"type": "empty_srt"})
    for block_number, block in enumerate(blocks, 1):
        lines = block.splitlines()
        if len(lines) < 3 or not lines[0].strip().isdigit():
            errors.append({"block": block_number, "type": "invalid_block", "detail": "Expected index, time range and caption text"})
            continue
        index = int(lines[0].strip())
        if index != block_number:
            warnings.append({"block": block_number, "type": "nonsequential_index", "index": index})
        match = RANGE.fullmatch(lines[1].strip())
        if not match:
            errors.append({"block": block_number, "type": "invalid_timestamp", "value": lines[1]})
            continue
        start, end = seconds(match.groups()[:4]), seconds(match.groups()[4:])
        cue_count += 1
        if end <= start:
            errors.append({"block": block_number, "type": "nonpositive_duration", "start": start, "end": end})
        if start < previous_start:
            errors.append({"block": block_number, "type": "out_of_order"})
        if start < previous_end - 0.001:
            errors.append({"block": block_number, "type": "overlap", "start": start, "previous_end": previous_end})
        if duration is not None and end > duration + 0.001:
            errors.append({"block": block_number, "type": "end_after_media", "end": end, "media_duration": duration})
        if not "\n".join(lines[2:]).strip():
            errors.append({"block": block_number, "type": "empty_caption"})
        previous_start, previous_end = start, end
        last_end = max(last_end, end)
    return {
        "structure_ok": not errors, "cue_count": cue_count,
        "last_end_seconds": round(last_end, 3), "media_duration_seconds": duration,
        "media_sync_checked": False,
        "note": "仅检查格式与时间结构；音画同步、字词正确、阅读速度和安全区仍需实际检查。",
        "errors": errors, "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--duration", type=float, help="Actual final media duration in seconds, if measured")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output and args.output.resolve() == args.file.resolve():
        parser.error("--output must not overwrite the input SRT")
    if args.duration is not None and (not 0 < args.duration < float("inf")):
        parser.error("--duration must be a positive finite number")
    try:
        result = validate(args.file.read_text(encoding="utf-8-sig"), args.duration)
        result["file"] = str(args.file)
        output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8")
            print(json.dumps({"output": str(args.output), "structure_ok": result["structure_ok"]}, ensure_ascii=False))
        else:
            print(output, end="")
        return 0 if result["structure_ok"] else 1
    except (OSError, UnicodeError) as exc:
        print(f"validate_srt: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
