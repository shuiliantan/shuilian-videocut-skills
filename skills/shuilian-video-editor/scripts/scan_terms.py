#!/usr/bin/env python3
"""Report personal wording candidates without rewriting source files."""
import argparse
import json
from pathlib import Path
import re
import sys


SKILL_ROOT = Path(__file__).resolve().parents[1]
TIMECODE = re.compile(r"\d{2,}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2,}:\d{2}:\d{2},\d{3}")


def load_rules(wordlist, additions):
    rules = {}
    for raw_line in wordlist.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "：" in line:
            left, right = line.split("：", 1)
            term = re.sub(r"\s*替换成\s*$", "", left).strip()
            if not right.strip():
                continue
            options = [value.strip() for value in re.split(r"或者|或", right) if value.strip()]
            rules[term] = {
                "handling": "发布字幕按词表映射替换，先复核完整词、专业术语和专名；同一视频统一写法",
                "replacement_options": options,
            }
        else:
            for term in line.split("、"):
                term = re.sub(r"等等$", "", term.strip())
                if term:
                    rules.setdefault(term, {"handling": "按语境检查并自然准确改写，不能确定则列待处理"})
    data = json.loads(additions.read_text(encoding="utf-8-sig"))
    for item in data["rules"]:
        rules[item["term"]] = {
            "handling": item["handling"],
            "replacement_options": item.get("replacement_options", []),
        }
    if not rules:
        raise ValueError("Personal wording list is empty")
    return rules


def scan_file(path, rules, pattern):
    source = path.read_text(encoding="utf-8-sig")
    findings = []
    current_timecode = None
    for line_number, line in enumerate(source.splitlines(), 1):
        if not line.strip():
            current_timecode = None
        if path.suffix.lower() == ".srt" and TIMECODE.fullmatch(line.strip()):
            current_timecode = line.strip()
        for match in pattern.finditer(line):
            term = match.group(0)
            findings.append({
                "file": str(path), "line": line_number, "column": match.start() + 1,
                "timecode": current_timecode, "term": term, "context": line,
                "handling": rules[term]["handling"], "requires_context_review": True,
                "replacement_options": rules[term].get("replacement_options", []),
            })
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path, help="UTF-8 text or SRT files to scan")
    parser.add_argument("--wordlist", type=Path, default=SKILL_ROOT / "references" / "wording-list.txt")
    parser.add_argument("--additions", type=Path, default=SKILL_ROOT / "references" / "wording-additions.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    protected_paths = {p.resolve() for p in [*args.files, args.wordlist, args.additions]}
    if args.output and args.output.resolve() in protected_paths:
        parser.error("--output must not overwrite an input file or wording resource")
    try:
        rules = load_rules(args.wordlist, args.additions)
        terms = sorted(rules, key=lambda term: (-len(term), term))
        pattern = re.compile("|".join(re.escape(term) for term in terms))
        findings = []
        for path in args.files:
            findings.extend(scan_file(path, rules, pattern))
        result = {
            "status": "candidates_found" if findings else "no_candidates",
            "read_only": True, "rule_count": len(rules), "candidate_count": len(findings),
            "note": "只读候选与用户给定替换写法；复核完整词、术语和语境后用于发布字幕，空选项需按语境处理，不代表平台审核结论。",
            "findings": findings,
        }
        output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8")
            print(json.dumps({"output": str(args.output), "candidate_count": len(findings)}, ensure_ascii=False))
        else:
            print(output, end="")
        return 0
    except (OSError, UnicodeError, ValueError, KeyError) as exc:
        print(f"scan_terms: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
