import csv, json, collections, datetime, os
rows=list(csv.DictReader(open("tracking/matter-tracker.csv")))
by=collections.Counter(r["Stage"] for r in rows)
report=f"""# Weekly Status Report\nGenerated: {datetime.datetime.utcnow().date()}\n\nTotal active matters: {len(rows)}\n\n## By Stage\n"""
for stage,count in by.items():
    report+=f"- {stage}: {count}\n"
report+="\n## High-risk matters\n"
for r in rows:
    if r["Risk_Level"]=="High":
        report+=f"- {r['Matter_ID']} {r['Client']} — {r['Next_Action']}\n"
open("tracking/weekly-report.md","w").write(report)
print("done")
