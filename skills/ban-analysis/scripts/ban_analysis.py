#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ban位推测工具 v2 — 通过数据对比找出某阵容的ban位
用法: python ban_analysis.py --our 596,573,592 --dt-start 2026-07-20 --dt-end 2026-07-26 --name 神龙平

参数:
  --our            我方前三手式神ID,逗号分隔 (必填)
  --dt-start       数据起始日期 (必填)
  --dt-end         数据截止日期 (必填)
  --name           阵容名称(可选)
  --output         输出文件路径 (可选,默认stdout)
"""
import subprocess, sys, argparse, os, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

MYSQL = r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe'
DB_ARGS = ['-u', 'root', '-p123456', '-D', 'yys']

def q(sql):
    cmd = [MYSQL] + DB_ARGS + ['-e', sql]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        err = r.stderr.strip() if r.stderr else ''
        clean_err = '\n'.join(l for l in err.split('\n') if 'Warning' not in l and 'insecure' not in l)
        if clean_err.strip():
            print(f'[SQL Error] {clean_err}', file=sys.stderr)
        return []
    lines = r.stdout.strip().split('\n')
    if len(lines) < 2:
        return []
    headers = [h.strip() for h in lines[0].split('\t')]
    rows = []
    for line in lines[1:]:
        vals = [v.strip() for v in line.split('\t')]
        if len(vals) == len(headers):
            rows.append(dict(zip(headers, vals)))
    return rows

def get_alias(info):
    parts = [p.strip() for p in info.get('aliases', info.get('name', '')).split(',') if p.strip()]
    return min(parts, key=len) if parts else '?'

def verify_ban(sid, our_ids, dt_start, dt_end, id_cond, si):
    """对某个嫌疑人跑50高频玩家验证"""
    players = q(f'''
        SELECT r.role_id, COUNT(*) AS c FROM ranking_battle_detail d
        JOIN ranking r ON r.id = d.id
        WHERE r.dt >= '{dt_start}' AND r.dt <= '{dt_end}' AND {id_cond}
        GROUP BY r.role_id ORDER BY c DESC LIMIT 50
    ''')
    zero, low, high = 0, 0, 0
    for p in players:
        cnt = int(q(f'''
            SELECT COUNT(*) AS c FROM ranking_battle_detail d
            JOIN ranking r ON r.id = d.id
            WHERE r.dt >= '{dt_start}' AND r.dt <= '{dt_end}'
              AND r.role_id = '{p['role_id']}' AND {id_cond}
              AND {sid} IN (d.battle_shi_shen_id1,d.battle_shi_shen_id2,d.battle_shi_shen_id3,
                            d.battle_shi_shen_id4,d.battle_shi_shen_id5,
                            d.d_battle_shi_shen_id1,d.d_battle_shi_shen_id2,d.d_battle_shi_shen_id3,
                            d.d_battle_shi_shen_id4,d.d_battle_shi_shen_id5)
        ''')[0]['c'])
        if cnt == 0: zero += 1
        elif cnt <= 5: low += 1
        else: high += 1
    total = len(players)
    zp = round(zero / total * 100, 1)
    return {'zero': zero, 'low': low, 'high': high, 'total': total, 'zero_pct': zp}

def main():
    parser = argparse.ArgumentParser(description='Ban位推测工具 v2')
    parser.add_argument('--our', required=True, help='我方前三手式神ID,逗号分隔')
    parser.add_argument('--dt-start', required=True, help='数据起始日期 YYYY-MM-DD')
    parser.add_argument('--dt-end', required=True, help='数据截止日期 YYYY-MM-DD')
    parser.add_argument('--name', default='', help='阵容名称')
    parser.add_argument('--output', default=None, help='输出文件路径')
    args = parser.parse_args()

    our_ids = sorted([int(x.strip()) for x in args.our.split(',')])
    name = args.name or '+'.join(str(x) for x in our_ids)

    id_cond = ' AND '.join([
        f'(d.battle_shi_shen_id1={sid} OR d.battle_shi_shen_id2={sid} OR d.battle_shi_shen_id3={sid})'
        for sid in our_ids
    ])

    # Step 1: 式神名称
    name_rows = q(f'SELECT id, name, aliases FROM shi_shen_lu WHERE id IN ({",".join(str(x) for x in our_ids)})')
    id_info = {int(r['id']): r for r in name_rows}
    lineup_names = ' + '.join(get_alias(id_info.get(sid, {})) for sid in our_ids)

    total = int(q(f'''
        SELECT COUNT(*) AS t FROM ranking_battle_detail d
        JOIN ranking r ON r.id = d.id
        WHERE r.dt >= '{args.dt_start}' AND r.dt <= '{args.dt_end}' AND {id_cond}
    ''')[0]['t'])
    if total == 0:
        print(f'无数据: {name} ({lineup_names}) 在 {args.dt_start}~{args.dt_end}')
        return

    gt = int(q(f'''
        SELECT COUNT(*) AS t FROM ranking_battle_detail d
        JOIN ranking r ON r.id = d.id
        WHERE r.dt >= '{args.dt_start}' AND r.dt <= '{args.dt_end}'
    ''')[0]['t'])

    # ==== 动态热门式神: 取全局对方出场率最高的前24名 ====
    hot_rows = q(f'''
        SELECT s.id, s.name, s.aliases, COUNT(*) AS cnt
        FROM ranking_battle_detail d
        JOIN ranking r ON r.id = d.id
        JOIN shi_shen_lu s ON s.id IN (d.d_battle_shi_shen_id1,d.d_battle_shi_shen_id2,
             d.d_battle_shi_shen_id3,d.d_battle_shi_shen_id4,d.d_battle_shi_shen_id5)
        WHERE r.dt >= '{args.dt_start}' AND r.dt <= '{args.dt_end or args.dt_start}'
        GROUP BY s.id, s.name, s.aliases
        ORDER BY cnt DESC
        LIMIT 30
    ''')
    hot_ids = [int(r['id']) for r in hot_rows]
    hot_str = ','.join(str(x) for x in hot_ids)
    si = {int(r['id']): r for r in hot_rows}

    go = {}
    for r in q(f'''
        SELECT s.id, COUNT(*) AS c FROM ranking_battle_detail d
        JOIN ranking r ON r.id = d.id
        JOIN shi_shen_lu s ON s.id IN (d.d_battle_shi_shen_id1,d.d_battle_shi_shen_id2,d.d_battle_shi_shen_id3,d.d_battle_shi_shen_id4,d.d_battle_shi_shen_id5)
        WHERE r.dt >= '{args.dt_start}' AND r.dt <= '{args.dt_end}' AND s.id IN ({hot_str})
        GROUP BY s.id
    '''): go[int(r['id'])] = int(r['c'])

    lo = {}
    for r in q(f'''
        SELECT s.id, COUNT(*) AS c FROM ranking_battle_detail d
        JOIN ranking r ON r.id = d.id
        JOIN shi_shen_lu s ON s.id IN (d.d_battle_shi_shen_id1,d.d_battle_shi_shen_id2,d.d_battle_shi_shen_id3,d.d_battle_shi_shen_id4,d.d_battle_shi_shen_id5)
        WHERE r.dt >= '{args.dt_start}' AND r.dt <= '{args.dt_end}' AND {id_cond} AND s.id IN ({hot_str})
        GROUP BY s.id
    '''): lo[int(r['id'])] = int(r['c'])

    lb = {}
    for r in q(f'''
        SELECT s.id, COUNT(*) AS c FROM ranking_battle_detail d
        JOIN ranking r ON r.id = d.id
        JOIN shi_shen_lu s ON s.id IN (
            d.battle_shi_shen_id1,d.battle_shi_shen_id2,d.battle_shi_shen_id3,
            d.battle_shi_shen_id4,d.battle_shi_shen_id5,
            d.d_battle_shi_shen_id1,d.d_battle_shi_shen_id2,d.d_battle_shi_shen_id3,
            d.d_battle_shi_shen_id4,d.d_battle_shi_shen_id5)
        WHERE r.dt >= '{args.dt_start}' AND r.dt <= '{args.dt_end}' AND {id_cond} AND s.id IN ({hot_str})
        GROUP BY s.id
    '''): lb[int(r['id'])] = int(r['c'])

    candidates = []
    for sid in hot_ids:
        gp = go.get(sid, 0) / gt * 100 if gt else 0
        lp = lo.get(sid, 0) / total * 100 if total else 0
        bc = lb.get(sid, 0)
        drop = round((gp - lp) / gp * 100, 1) if gp > 0 else 0
        info = si.get(sid, {})
        candidates.append({
            'id': sid, 'name': info.get('name', str(sid)), 'alias': get_alias(info),
            'gp': round(gp, 1), 'lp': round(lp, 1), 'drop': drop, 'bc': bc
        })

    candidates.sort(key=lambda x: -x['drop'])

    # ==== 两轮验证策略 ====
    # 第一轮: 跌幅 >= 80% 且 全局 >= 3%
    level1 = [c for c in candidates if c['drop'] >= 80 and c['gp'] >= 3]
    verified = {}
    for s in level1:
        verified[s['id']] = verify_ban(s['id'], our_ids, args.dt_start, args.dt_end, id_cond, si)

    # 第二轮: 如果第一轮没出确认结果, 扩展验证跌幅 >= 50% 且全局 >= 5%的
    confirmed = [k for k, v in verified.items() if v['zero_pct'] >= 80]
    if not confirmed:
        level2 = [c for c in candidates if c['drop'] >= 50 and c['gp'] >= 5 and c['id'] not in verified]
        for s in level2:
            verified[s['id']] = verify_ban(s['id'], our_ids, args.dt_start, args.dt_end, id_cond, si)

    # 再确认一次
    confirmed = [k for k, v in verified.items() if v['zero_pct'] >= 80]
    maybes = [k for k, v in verified.items() if 50 <= v['zero_pct'] < 80]

    # ========== 输出 ==========
    lines = []
    lines.append('=' * 65)
    lines.append(f' Ban位分析报告: {name}')
    lines.append(f' 阵容: {lineup_names}  | 式神ID: {",".join(str(x) for x in our_ids)}')
    lines.append(f' 时间: {args.dt_start} ~ {args.dt_end}')
    lines.append(f' 总场次: {total:,}  | 全局对局: {gt:,}')
    lines.append('=' * 65)
    lines.append('')
    lines.append('─' * 65)
    lines.append(' 热门式神 出场率对比 (对方侧)')
    lines.append('─' * 65)
    lines.append(f' {"式神":<10} {"简称":<6} {"全局%":>7} {"阵容%":>7} {"跌幅%":>7} {"合计":>6}  判定')
    lines.append('─' * 65)

    for c in candidates:
        if c['gp'] < 0.3:
            continue
        if c['id'] in confirmed:
            tag = 'BAN位✅'
        elif c['id'] in maybes:
            tag = '高度疑似'
        elif c['drop'] >= 50 and c['gp'] >= 5:
            tag = '可能'
        elif c['drop'] <= -20:
            tag = '反增📈'
        else:
            tag = '正常'
        lines.append(f' {c["name"]:<10} {c["alias"]:<6} {c["gp"]:>6}% {c["lp"]:>6}% {c["drop"]:>6}% {c["bc"]:>6}  {tag}')

    lines.append('─' * 65)
    lines.append('')

    if verified:
        lines.append('─' * 65)
        lines.append(' 【50高频玩家验证】')
        lines.append('─' * 65)
        for sid, v in sorted(verified.items(), key=lambda x: -x[1]['zero_pct']):
            info = si.get(sid, {})
            sname = info.get('name', str(sid))
            ct = 'BAN位确认' if v['zero_pct'] >= 80 else ('高度疑似' if v['zero_pct'] >= 50 else '需核查')
            lines.append(f'  {sname}({get_alias(info)}): {v["zero"]}/{v["total"]}人从未出现 ({v["zero_pct"]}%)  {ct}')
            lines.append(f'    分布: 0次={v["zero"]}人  1~5次={v["low"]}人  >5次={v["high"]}人')
        lines.append('')

    if confirmed:
        lines.append('=' * 65)
        lines.append(f' 【结论】{name} 的ban位是:')
        for sid in confirmed:
            info = si.get(sid, {})
            sname = info.get('name', str(sid))
            v = verified[sid]
            # 找到对应的candidate数据
            cand = [c for c in candidates if c['id'] == sid][0]
            lines.append(f'   {sname}({get_alias(info)}, ID:{sid})')
            lines.append(f'     数据: 全局{cand["gp"]}% → 对局仅{cand["lp"]}% (跌幅{cand["drop"]}%)')
            lines.append(f'     验证: {v["zero"]}/{v["total"]}高频玩家从未出现({v["zero_pct"]}%)')
        lines.append('=' * 65)
    elif maybes:
        lines.append('─' * 65)
        lines.append(f' 【疑似】以下式神可能是ban位，需人工确认:')
        for sid in maybes:
            info = si.get(sid, {})
            v = verified[sid]
            cand = [c for c in candidates if c['id'] == sid][0]
            lines.append(f'   {info.get("name", str(sid))}: 全局{cand["gp"]}%→{cand["lp"]}%, 50人中{v["zero"]}人未出现')
        lines.append('─' * 65)
    else:
        lines.append('⚠️ 未检测到明确ban位，可能该阵容ban位不固定或数据不足')

    output = '\n'.join(lines)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f'[输出] 报告已保存至: {args.output}')
    else:
        print(output)

if __name__ == '__main__':
    main()
