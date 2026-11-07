#!/usr/bin/env python3
"""Create an offline, static storyboard review from SRT; never render video."""
import argparse
import base64
from html import escape
import json
from pathlib import Path
import re
import sys

from validate_srt import RANGE, seconds, validate

KINDS = {"presenter": "本人动态口播", "screen": "操作实录", "real": "真实图片", "diagram": "关系图解"}
FIELDS = {"source": "素材来源", "visual": "画面任务", "motion": "镜头动作", "hold": "阅读停留", "presenter_area": "人物区域", "notes": "备注"}


def read_cues(text):
    report = validate(text)
    if not report["structure_ok"]:
        raise ValueError("Invalid SRT: " + json.dumps(report["errors"], ensure_ascii=False))
    normalized = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").strip()
    cues = []
    for block in re.split(r"\n[ \t]*\n", normalized):
        lines = block.splitlines()
        m = RANGE.fullmatch(lines[1].strip())
        cues.append({"id": int(lines[0]), "start": seconds(m.groups()[:4]),
                     "end": seconds(m.groups()[4:]), "time": lines[1].strip(), "text": "\n".join(lines[2:])})
    if len({c["id"] for c in cues}) != len(cues):
        raise ValueError("SRT cue IDs must be unique")
    return cues


def default_shots(cues):
    return [{"id": f"{i:02d}", "cue_ids": [c["id"]], "kind": "presenter", "asset": "",
             **{field: "" for field in FIELDS}} for i, c in enumerate(cues, 1)]


def validate_shots(shots, cues):
    if not isinstance(shots, list) or not shots:
        raise ValueError("shots must be a nonempty JSON array")
    covered, ids = [], set()
    for s in shots:
        if not isinstance(s, dict):
            raise ValueError("Each shot must be an object")
        sid = s.get("id")
        if not isinstance(sid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", sid) or sid in ids:
            raise ValueError("Shot IDs must be unique ASCII letters/digits/underscore/hyphen")
        ids.add(sid)
        if s.get("kind") not in KINDS:
            raise ValueError(f"Unknown kind in shot {sid}")
        members = s.get("cue_ids")
        if not isinstance(members, list) or not members or any(type(i) is not int for i in members):
            raise ValueError(f"Invalid cue_ids in shot {sid}")
        covered.extend(members)
        for key in ["asset", *FIELDS]:
            if not isinstance(s.get(key, ""), str):
                raise ValueError(f"{key} must be text in shot {sid}")
    if covered != [c["id"] for c in cues]:
        raise ValueError("Shots must cover every cue exactly once and in SRT order")


def embedded_image(asset, root):
    if not asset:
        return None
    p = Path(asset)
    if p.is_absolute():
        raise ValueError("Asset must be relative to the shots JSON folder")
    p = (root / p).resolve()
    if not p.is_relative_to(root.resolve()):
        raise ValueError("Asset must stay inside the shots JSON folder")
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(p.suffix.lower())
    if not mime or p.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("Asset must be PNG/JPEG/WEBP, no larger than 10 MiB")
    data = p.read_bytes()
    valid = ((mime == "image/png" and data.startswith(b"\x89PNG\r\n\x1a\n")) or
             (mime == "image/jpeg" and data.startswith(b"\xff\xd8\xff")) or
             (mime == "image/webp" and data.startswith(b"RIFF") and data[8:12] == b"WEBP"))
    if not valid:
        raise ValueError("Image signature does not match its extension")
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def build_html(cues, shots, root):
    validate_shots(shots, cues)
    by_id = {c["id"]: c for c in cues}
    cards = []
    for s in shots:
        members = [by_id[i] for i in s["cue_ids"]]
        title = escape(s.get("visual") or "待填写画面任务")
        data = embedded_image(s.get("asset", ""), root)
        preview = f'<img src="{data}" alt="分镜 {escape(s["id"])} 代表帧">' if data else f'<div class="placeholder"><small>尚未添加代表帧</small><p>{title}</p></div>'
        captions = "".join(f'<li><small>{escape(c["time"])}</small><p>{escape(c["text"])}</p></li>' for c in members)
        details = "".join(f'<div><dt>{label}</dt><dd>{escape(s.get(key) or "待填写")}</dd></div>' for key, label in FIELDS.items())
        cards.append(f'''<article data-id="{escape(s['id'])}">
<div class="preview">{preview}<span>静态代表帧 / 方案说明 · 非动画预览</span></div>
<section><header><h2>分镜 {escape(s['id'])}</h2><b>{KINDS[s['kind']]}</b></header>
<p class="range">{members[0]['start']:.3f}s — {members[-1]['end']:.3f}s</p>
<ul class="captions">{captions}</ul><dl>{details}</dl>
<label>核对状态 <select aria-label="分镜 {s['id']} 核对状态"><option value="pending">待核对</option><option value="revise">需修改</option><option value="approved">方案通过</option></select></label>
<label class="feedback">修改意见<textarea aria-label="分镜 {s['id']} 修改意见" placeholder="按段号描述：哪个画面、哪里不对、怎么改"></textarea></label>
</section></article>''')
    return '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'">
<title>水莲剪辑 · 分镜核对</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3f6fa;color:#182c3b;font:16px/1.65 system-ui,'Noto Sans CJK SC',sans-serif}
main{max-width:1160px;margin:38px auto;padding:0 24px}.mast{display:flex;justify-content:space-between;align-items:center;gap:24px}h1{font-size:30px;margin:0}.intro{color:#536778;margin:8px 0 28px}button{background:#135f73;color:white;border:0;border-radius:8px;padding:13px 20px;font:inherit;cursor:pointer;white-space:nowrap}
article{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);background:white;border:1px solid #dce5eb;border-radius:14px;overflow:hidden;margin-bottom:26px}.preview{padding:24px;background:#eaf0f4;display:flex;flex-direction:column;justify-content:center}.preview img{max-width:100%;max-height:500px;object-fit:contain}.preview>span{font-size:12px;color:#657a89;margin-top:16px}.placeholder{border:1px dashed #afc4cf;border-radius:10px;padding:32px;min-height:240px;display:flex;flex-direction:column;justify-content:center}.placeholder small{color:#496c7c}.placeholder p{font-size:24px;font-weight:600;line-height:1.6;overflow-wrap:anywhere}section{padding:24px}header{display:flex;align-items:center;justify-content:space-between;gap:16px}h2{font-size:22px;margin:0}header b{font-size:13px;color:#196f76}.range{font-variant-numeric:tabular-nums;color:#657a89;font-size:13px;margin:2px 0 16px}.captions{list-style:none;padding:0;margin:0 0 20px}.captions li{padding:8px 0;border-bottom:1px solid #edf1f4}.captions small{font-size:11px;color:#607584}.captions p{margin:2px 0;white-space:pre-wrap;overflow-wrap:anywhere}dl{font-size:14px}dl div{display:grid;grid-template-columns:70px 1fr;gap:8px;margin:9px 0}dt{color:#607584}dd{margin:0;white-space:pre-wrap;overflow-wrap:anywhere}label{font-size:14px}select{margin-left:12px;padding:5px;border:1px solid #bbcdd7;border-radius:5px;font:inherit}.feedback{display:block;margin-top:14px}textarea{width:100%;min-height:78px;resize:vertical;border:1px solid #bbcdd7;border-radius:7px;padding:10px;font:inherit;display:block;margin-top:7px}footer{font-size:13px;color:#607584;margin:20px 0 50px}@media(max-width:760px){article{grid-template-columns:1fr}.mast{align-items:flex-start;flex-direction:column}.placeholder{min-height:160px}main{padding:0 14px}h1{font-size:25px}}
</style></head><body><main><div class="mast"><h1>水莲剪辑 · 分镜核对</h1><button id="export">导出反馈 JSON</button></div>
<p class="intro">依据字幕时间核对画面方案。当前页面不播放视频或动画，不自动保存输入；关闭前请导出反馈。</p>
''' + "\n".join(cards) + '''<footer>方案通过仅表示该分镜方案确认。动态画面、口型、字幕同步和混音仍须检查实际导出视频。</footer></main>
<script>document.getElementById('export').addEventListener('click',()=>{
const shots=[...document.querySelectorAll('article')].map(el=>({id:el.dataset.id,status:el.querySelector('select').value,feedback:el.querySelector('textarea').value}));
const blob=new Blob([JSON.stringify({type:'storyboard_feedback',created_at:new Date().toISOString(),shots},null,2)],{type:'application/json'});
const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='storyboard-feedback.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});</script></body></html>'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("srt", type=Path)
    p.add_argument("--shots", type=Path)
    p.add_argument("--write-shots", type=Path, help="Create a new shot template; never overwrite")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    try:
        if args.shots and args.write_shots:
            raise ValueError("Use --shots OR --write-shots")
        inputs = {args.srt.resolve()}
        if args.shots:
            inputs.add(args.shots.resolve())
        if args.out.resolve() in inputs or (args.write_shots and args.out.resolve() == args.write_shots.resolve()):
            raise ValueError("Output cannot overwrite an input or the shot template")
        if args.write_shots and (args.write_shots.exists() or args.write_shots.resolve() in inputs):
            raise ValueError("--write-shots destination already exists or is an input")
        cues = read_cues(args.srt.read_text(encoding="utf-8-sig"))
        shots = json.loads(args.shots.read_text(encoding="utf-8-sig")) if args.shots else default_shots(cues)
        html = build_html(cues, shots, args.shots.parent if args.shots else args.srt.parent)
        if args.write_shots:
            args.write_shots.parent.mkdir(parents=True, exist_ok=True)
            with args.write_shots.open("x", encoding="utf-8") as f:
                f.write(json.dumps(shots, ensure_ascii=False, indent=2) + "\n")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(html, encoding="utf-8")
        print(json.dumps({"html": str(args.out), "shots": len(shots), "cues": len(cues), "video_rendered": False}, ensure_ascii=False))
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"review_storyboard: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
