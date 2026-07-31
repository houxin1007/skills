#!/usr/bin/env python3
"""
斗技阵容决策树 HTML 生成器
用法: python generate_decision_tree.py --our 596,573,592 --ban 597 --dt-start 2026-07-20 --dt-end 2026-07-26 --min-matches 200 --output 神龙平_决策树.html

参数说明:
  --our         我方前三手式神ID,逗号分隔 (必填)
  --ban         禁用的式神ID (可选,可多个逗号分隔)
  --dt-start    数据起始日期 (可选, 空=不限)
  --dt-end      数据截止日期 (可选, 空=不限)
  --min-matches 最低对局场次,低于此数不展示 (默认200)
  --output      输出HTML文件名 (默认 决策树.html)
  --title       页面标题 (可选)
"""
import subprocess, sys, argparse, os
from collections import defaultdict, Counter

MYSQL = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"

def query(sql):
    r = subprocess.run([MYSQL,"-u","root","-p123456","--default-character-set=utf8mb4","-N","-D","yys","-e",sql],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [l.strip() for l in r.stdout.strip().split("\n") if l.strip() and "Warning" not in l]

def wr(t,w):
    return w/t*100 if t else 0

def show(t, bt, pct, wval, mn=20):
    if t < mn: return False
    if wval >= 67: return True
    if wval < 40: return False
    return t >= max(int(bt*pct/100), mn)

def ensure5_low(all_o, filt):
    if len(filt) >= 5: return filt
    res = list(filt)
    ks = {r["key"] for r in res}
    for o in sorted([o for o in all_o if o["key"] not in ks], key=lambda x: -x["total"]):
        if len(res) >= 5: break
        res.append(o)
    return res


def ensure5(all_o, filt):
    if len(filt) >= 5: return filt
    res = list(filt)
    ks = {r["key"] for r in res}
    for o in sorted([o for o in all_o if o["key"] not in ks], key=lambda x: -x["total"]):
        if len(res) >= 5: break
        if wr(o["total"], o["wins"]) >= 40: res.append(o)
    return res

def build_tree(battles, shen_alias, min_matches):
    ct = Counter(b["e3"] for b in battles)
    combos = {k:v for k,v in ct.items() if v >= min_matches}
    combos = dict(sorted(combos.items(), key=lambda x: -x[1]))

    tree = []
    for combo, total in combos.items():
        cb = [b for b in battles if b["e3"] == combo]
        m4all = defaultdict(list)
        for b in cb: m4all[b["m"][3]].append(b)

        m4l = []
        for sid, sbl in m4all.items():
            w = sum(1 for b in sbl if b["r"]==1); t = len(sbl); rw = wr(t,w)
            if show(t, total, 1, rw): m4l.append({"key":sid, "wins":w, "total":t, "wr":rw, "battles":sbl})
        m4l = [m for m in m4l if m["key"] not in OUR]
        all4 = [{"key":sid,"wins":sum(1 for b in bl if b["r"]==1),"total":len(bl),
                 "wr":wr(len(bl),sum(1 for b in bl if b["r"]==1)),"battles":bl}
                for sid,bl in sorted(m4all.items(),key=lambda x:-len(x[1])) if sid not in OUR]
        m4l = ensure5(all4, m4l)
        m4l.sort(key=lambda x: -x["total"])

        for m4 in m4l:
            ea = defaultdict(list)
            for b in m4["battles"]: ea[b["e"][3]].append(b)
            en = []  # normal (wr>=40)
            el = []  # low (wr<40)
            for eid, ebl in ea.items():
                w=sum(1 for b in ebl if b["r"]==1); t=len(ebl); rw=wr(t,w)
                item = {"key":eid,"wins":w,"total":t,"wr":rw,"battles":ebl}
                if show(t, m4["total"], 3, rw):
                    en.append(item)
                elif rw < 40 and t >= 20:
                    el.append(item)
            all_e = [{"key":eid,"wins":sum(1 for b in bl if b["r"]==1),"total":len(bl),
                      "wr":wr(len(bl),sum(1 for b in bl if b["r"]==1)),"battles":bl}
                     for eid,bl in sorted(ea.items(),key=lambda x:-len(x[1]))]
            en = ensure5([x for x in all_e if x["wr"] >= 40 and x["key"] not in {r["key"] for r in el}], en)
            ek = {r["key"] for r in en} | {r["key"] for r in el}
            el = ensure5_low([x for x in all_e if x["key"] not in ek], el)
            for e in el:
                if e["wr"] < 40: e["low"] = True
            en.sort(key=lambda x: -x["total"]); el.sort(key=lambda x: -x["total"])
            el = en + el

            for e4 in el:
                e5d = Counter()
                m5d = defaultdict(lambda:[0,0])
                for b in e4["battles"]:
                    m5=b["m"][4]; m5d[m5][0]+=1
                    if b["r"]==1: m5d[m5][1]+=1
                    e5=b["e"][4]
                    if e5: e5d[e5]+=1
                ml = []
                for mid,(t,w) in m5d.items():
                    rw=wr(t,w)
                    if show(t, e4["total"], 5, rw): ml.append({"key":mid,"wins":w,"total":t,"wr":rw})
                all_m = [{"key":mid,"wins":w,"total":t,"wr":wr(t,w)}
                         for mid,(t,w) in sorted(m5d.items(),key=lambda x:-x[1][0])]
                ml = ensure5(all_m, ml)
                ml.sort(key=lambda x: -x["total"])
                e4["my5"] = ml
                el5 = sorted([{"key":k,"total":v} for k,v in e5d.items()], key=lambda x:-x["total"])[:10]
                e4["ene5"] = el5
            m4["ene4"] = el

        cn = "/".join(shen_alias.get(s,str(s)) for s in combo)
        tree.append({"combo":combo, "name":cn, "total":total, "my4":m4l})
    return tree

def gen_html(tree, shen_alias, shen_rarity, title, out_path):
    all_ids = set()
    for t in tree:
        for s in t["combo"]: all_ids.add(s)
    sp = sorted([s for s in all_ids if shen_rarity.get(s)==6],
                key=lambda s: -sum(1 for td in tree if s in td["combo"]))
    ssr = sorted([s for s in all_ids if shen_rarity.get(s,0)!=6],
                 key=lambda s: -sum(1 for td in tree if s in td["combo"]))

    ch = '<div class="fl-row">'
    if sp:
        ch += '<span style="font-size:11px;font-weight:bold;color:#8e44ad;min-width:28px">SP</span>'
        for s in sp:
            c = sum(1 for td in tree if s in td["combo"])
            ch += f'<span class="chip" data-id="{s}" onclick="tc(this)">{shen_alias.get(s,str(s))}<span class="ct">{c}组</span></span>'
    ch += '</div><div class="fl-row">'
    if ssr:
        ch += '<span style="font-size:11px;font-weight:bold;color:#c8a44e;min-width:28px">SSR</span>'
        for s in ssr:
            c = sum(1 for td in tree if s in td["combo"])
            ch += f'<span class="chip" data-id="{s}" onclick="tc(this)">{shen_alias.get(s,str(s))}<span class="ct">{c}组</span></span>'
    ch += '</div>'

    cds = ""
    for td in tree:
        ck = "_".join(str(s) for s in td["combo"])
        body = ""
        for m4 in td["my4"]:
            sn = shen_alias.get(m4["key"],str(m4["key"]))
            ws = f"{m4['wr']:.1f}%".replace(".0%","%")
            body += f'<div class="p4row" onclick="tog(this)"><span class="p4n">{sn}</span><span class="p4wr">{ws}</span><span class="p4ct">{m4["total"]}</span><span class="arr">▸</span></div><div class="p5d">'
            for e4 in m4["ene4"]:
                en = shen_alias.get(e4["key"],str(e4["key"]))
                ews = f"{e4['wr']:.1f}%".replace(".0%","%")
                body += f'<div class="op4h{" low" if e4.get("low") else ""}">对方\u00b7{en} <span class="op4s">({e4["total"]}局, 我胜率{ews})</span></div>'
                mxw = max((x["wr"] for x in e4["my5"]), default=0)
                for m5 in e4["my5"]:
                    m5n = shen_alias.get(m5["key"],str(m5["key"]))
                    m5w = f"{m5['wr']:.1f}%".replace(".0%","%")
                    bw = min(round(m5["wr"]),100)
                    hl = " hl" if m5["wr"]>=mxw and m5["wr"]>0 else ""
                    body += f'<div class="p5row{hl}"><span class="p5n">{m5n}</span><span class="p5bar"><span style="width:{bw}%"></span></span><span class="p5wr">{m5w}</span><span class="p5ct">{m5["total"]}</span></div>'
                if e4.get("ene5"):
                    eparts = " / ".join(shen_alias.get(o["key"],str(o["key"]))+"("+str(o["total"])+")" for o in e4["ene5"])
                    body += f'<div style="font-size:9px;color:#888;padding:0 0 0 8px">对方五选：{eparts}</div>'
            body += "</div>"
        cds += f'<div class="card" data-combo="{ck}"><div class="ch"><span class="on">{td["name"]}</span><span class="ot">{td["total"]}局</span></div><div class="p4l">{body}</div></div>'

    html = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:Microsoft YaHei,sans-serif;background:#f0ebe3;padding:12px;font-size:13px}}
h1{{text-align:center;font-size:17px;color:#2c3e50;margin-bottom:2px}}.sub{{text-align:center;font-size:11px;color:#7f8c8d;margin-bottom:4px}}
.filter{{display:flex;flex-direction:column;gap:4px;margin-bottom:8px;padding:6px;background:#fff;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.fl-row{{display:flex;flex-wrap:wrap;gap:4px;align-items:center}}
.chip{{padding:3px 8px;border-radius:4px;font-size:11px;cursor:pointer;border:1px solid #ddd;background:#fff;color:#555;transition:all .15s;white-space:nowrap}}
.chip:hover{{border-color:#8e44ad;color:#8e44ad}}.chip.on{{background:#2c3e50;color:#fff;border-color:#2c3e50;flex:none}}
.chip .ct{{font-size:9px;color:#aaa;margin-left:3px}}.chip.on .ct{{color:#8ab4e8}}
.gd{{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}}
.card{{background:#fff;border-radius:8px;width:330px;box-shadow:0 2px 8px rgba(0,0,0,.05);transition:opacity .2s}}.card.hide{{display:none}}.low{{opacity:0.55}}.op4h.low::after{{content:" 劣势";font-size:9px;color:#e74c3c;margin-left:3px}}
.ch{{background:#2c3e50;color:#fff;padding:7px 10px;border-radius:8px 8px 0 0;display:flex;justify-content:space-between;align-items:center}}
.on{{font-size:12px;font-weight:bold;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}}.ot{{font-size:10px;color:#bdc3c7}}
.p4l{{padding:5px}}.p4row{{display:flex;align-items:center;padding:4px 5px;border-radius:4px;font-size:12px;cursor:pointer;gap:3px;margin-bottom:1px;background:#fff}}
.p4row:hover{{background:#eaf2f8!important}}
.p4n{{flex:1;color:#2c3e50;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.p4wr{{color:#e67e22;font-weight:bold;font-size:11px;min-width:34px;text-align:right}}
.p4ct{{color:#95a5a6;font-size:10px;min-width:30px;text-align:right}}.arr{{color:#bdc3c7;font-size:9px;transition:transform .2s}}
.p5d{{display:none;padding:3px 0 3px 6px;border-left:2px solid #eee;margin:1px 0 3px 6px}}.p5d.open{{display:block}}
.op4h{{font-size:11px;color:#8e44ad;font-weight:bold;margin-bottom:2px;margin-top:4px}}.op4s{{font-weight:normal;color:#95a5a6;font-size:10px}}
.p5row{{display:flex;align-items:center;padding:2px 4px;border-radius:3px;font-size:11px;gap:2px;margin-bottom:1px;background:#faf8f6}}
.p5row.hl{{font-weight:bold;background:#fff3cd}}.p5row:nth-child(even){{background:#f5f2ee}}
.p5n{{flex:0 0 50px;color:#2c3e50;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:10px}}
.p5bar{{flex:1;height:7px;background:#ecf0f1;border-radius:3px;overflow:hidden}}.p5bar span{{display:block;height:100%;background:#3498db;border-radius:3px}}
.p5wr{{flex:0 0 32px;text-align:right;color:#2c3e50;font-size:10px}}.p5ct{{flex:0 0 28px;text-align:right;color:#bdc3c7;font-size:9px}}
.ft{{text-align:center;color:#bdc3c7;font-size:10px;margin-top:14px}}#info{{text-align:center;font-size:11px;color:#8e44ad;margin:4px 0}}
</style></head><body><h1>{title}</h1><p class="sub">数据范围: {DT_START}~{DT_END}</p><div class="filter" style="margin-bottom:4px;padding:4px 8px">{ch}</div><p id="info">共{len(tree)}种对局</p><div class="gd" id="gd">{cds}</div><div class="ft">数据来源: yys斗技数据库</div><script>
function tc(el){{el.classList.toggle("on");af();}}
function af(){{
var on=document.querySelectorAll(".chip.on");
if(!on.length){{document.querySelectorAll(".card").forEach(function(c){{c.classList.remove("hide");}});document.getElementById("info").textContent="共{len(tree)}种对局";return;}}
var ids=[];on.forEach(function(c){{ids.push(parseInt(c.getAttribute("data-id")));}});
var v=0;
document.querySelectorAll(".card").forEach(function(c){{
var a=c.getAttribute("data-combo").split("_").map(Number);
if(ids.every(function(i){{return a.indexOf(i)>=0}})){{c.classList.remove("hide");v++;}}else{{c.classList.add("hide");}}
}});
document.getElementById("info").textContent="筛选后 "+v+" 种对局";
}}
function tog(el){{
var d=el.nextElementSibling;
if(d&&d.className.indexOf("p5d")>=0){{
if(d.className.indexOf("open")>=0){{d.className="p5d";el.querySelector(".arr").textContent="\u25b8";}}else{{d.className="p5d open";el.querySelector(".arr").textContent="\u25be";}}
}}
}}
</script></body></html>'''
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return len(tree)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成斗技阵容决策树HTML")
    parser.add_argument("--our", required=True, help="我方前三手式神ID,逗号分隔 如 596,573,592")
    parser.add_argument("--ban", default="", help="禁用的式神ID,逗号分隔")
    parser.add_argument("--dt-start", default="", help="数据起始日期 如 2026-07-20, 空=不限")
    parser.add_argument("--dt-end", default="", help="数据截止日期 如 2026-07-26, 空=不限")
    parser.add_argument("--min-matches", type=int, default=200, help="最低对局场次 (默认200)")
    parser.add_argument("--output", default="决策树.html", help="输出文件路径")
    parser.add_argument("--title", default="", help="页面标题")
    args = parser.parse_args()

    OUR = {int(x) for x in args.our.split(",")}
    BANS = {int(x) for x in args.ban.split(",") if x}
    DT_START = args.dt_start
    DT_END = args.dt_end
    MIN_MATCHES = args.min_matches
    TITLE = args.title or f"决策树 ({'/'.join(str(x) for x in OUR)})"

    print(f"查询条件: 我方{OUR}, ban{BANS}, {DT_START}~{DT_END}, >= {MIN_MATCHES}场", flush=True)

    # Load shishen data
    sl = query("SELECT id,name,aliases FROM shi_shen_lu;")
    sa, sr = {}, {}
    for l in sl:
        p = l.split("\t")
        sid = int(p[0]); name = p[1]
        raw = (p[2] if len(p)>2 and p[2].strip() else name)
        parts = [x.strip() for x in raw.split(",") if x.strip()]
        sa[sid] = min(parts, key=len) if parts else name
    for l in query("SELECT id,rarity FROM shi_shen_lu;"):
        p = l.split("\t")
        sr[int(p[0])] = int(p[1])
    print(f"式神数据加载: {len(sa)} 个", flush=True)

    # Query battles
    raw = query(f'SELECT rbd.battle_result,rbd.battle_shi_shen_id1,rbd.battle_shi_shen_id2,'
                f'rbd.battle_shi_shen_id3,rbd.battle_shi_shen_id4,rbd.battle_shi_shen_id5,'
                f'rbd.d_battle_shi_shen_id1,rbd.d_battle_shi_shen_id2,rbd.d_battle_shi_shen_id3,'
                f'rbd.d_battle_shi_shen_id4,rbd.d_battle_shi_shen_id5 '
                f'FROM ranking_battle_detail rbd JOIN ranking r ON rbd.id=r.id '
                f'WHERE rbd.battle_result IS NOT NULL' + (f' AND r.dt>="{DT_START}"' if DT_START else '') + (f' AND r.dt<="{DT_END}"' if DT_END else '') + ';')

    battles = []
    for l in raw:
        p = l.split("\t")
        if len(p) < 11: continue
        try:
            result = int(p[0])
            my = [int(p[i] or 0) for i in range(1,6)]
            en = [int(p[i] or 0) for i in range(6,11)]
            my_first3 = set(my[:3]) - {0}
            if my_first3 != OUR: continue
            es = set(en) - {0}
            if BANS and es & BANS: continue
            battles.append({"r":result,"m":my,"e":en,"e3":tuple(sorted(en[:3]))})
        except: pass

    print(f"有效对局: {len(battles)}", flush=True)
    if len(battles) < 100:
        print("数据不足, 退出", flush=True)
        sys.exit(1)

    tree = build_tree(battles, sa, MIN_MATCHES)
    cnt = gen_html(tree, sa, sr, TITLE, args.output)
    print(f"完成: {cnt} 种对局组合, 输出至 {args.output}", flush=True)