"""Merge multiple extraction result JSON files into one consolidated report."""

import json
import sys
from pathlib import Path

files = sys.argv[1:]
if not files:
    files = [
        Path("/coding/EAKIS/test_results/batch_extract_0-21_20260525_112630.json"),
        Path("/coding/EAKIS/test_results/mcp_extract_20260525_115322.json"),
    ]

merged = {"timestamp": None, "total_companies": 0, "total_articles": 0, "companies": []}
seen = {}  # company -> index in merged["companies"]

for fpath in files:
    p = Path(fpath)
    if not p.exists():
        print(f"  [SKIP] {fpath} not found")
        continue
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not merged["timestamp"]:
        merged["timestamp"] = data.get("timestamp", "")
    for cs in data.get("companies", []):
        company = cs["company"]
        if company in seen:
            idx = seen[company]
            merged["companies"][idx]["articles_extracted"] += cs["articles_extracted"]
            merged["companies"][idx]["successful"] += cs["successful"]
            merged["companies"][idx]["failed"] += cs.get("failed", 0)
            merged["companies"][idx]["results"].extend(cs.get("results", []))
        else:
            seen[company] = len(merged["companies"])
            merged["companies"].append(cs)

merged["total_companies"] = len(merged["companies"])
merged["total_articles"] = sum(cs["successful"] for cs in merged["companies"])

out_path = Path("/coding/EAKIS/test_results/batch_final_consolidated.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)

# Print summary
print(f"\n{'='*70}")
print(f"  合并结果 — {merged['total_companies']} 家企业，{merged['total_articles']} 篇有效提取")
print(f"  来源: {', '.join(str(p.name) for p in files)}")
print(f"{'='*70}")
for cs in merged["companies"]:
    results = cs.get("results", [])
    products_all = set()
    partners_all = set()
    for r in results:
        products_all.update(r.get("products", []))
        partners_all.update(r.get("partner_orgs", []))
    print(f"\n  【{cs['company']}】成功 {cs['successful']} 篇")
    if products_all:
        print(f"    产品/平台: {', '.join(sorted(products_all)[:8])}")
    if partners_all:
        print(f"    关联单位: {', '.join(sorted(partners_all)[:6])}")
    for i, r in enumerate(results, 1):
        print(f"    {i}. {r.get('summary', '')} [{r.get('event_type', '?')}]")

# Report missing companies
all_22 = [
    "中广电移动网络有限公司福建分公司", "三明市数据集团有限公司",
    "福建省三明数字城服科技股份有限公司", "福建省大数据集团漳州有限公司",
    "国网福建省电力有限公司", "福建省配电售电有限责任公司",
    "福州亿力电力工程有限公司", "厦门电力工程集团有限公司",
    "福建省中禹水利水电工程有限公司", "福建沿海电力集团有限公司",
    "福建环三电力工程有限公司", "福建水利电力职业技术学院",
    "中闽能源股份有限公司", "福建省建筑轻纺设计院有限公司",
    "国网福建省电力有限公司厦门供电公司", "福建省宁德市东电发展有限公司",
    "厦门市政水务集团有限公司", "石狮市锦尚环境工程有限公司",
    "石狮市祥芝环境工程有限公司", "漳浦发展水务有限公司",
    "漳州市角美自来水有限公司", "福建水投集团闽清水务有限公司",
]
found = set(cs["company"] for cs in merged["companies"])
missing = [c for c in all_22 if c not in found]
if missing:
    print(f"\n{'='*70}")
    print(f"  未收集到信息的企业 ({len(missing)} 家):")
    for c in missing:
        print(f"    - {c}")

print(f"\n  结果已保存: {out_path}")
