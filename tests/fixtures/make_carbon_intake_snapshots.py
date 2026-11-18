import json, sys
sys.path.insert(0, "avatar-intake")
import server as s
cases_prompt = [("guion-plan", "es", [], [], "calavera"), ("guion-plan-en", "en", ["documentos"], ["ahcd"], "avatar"),
                ("guion-plan", "es", ["documentos", "nombre", "nacimiento"], ["will", "trust"], "calavera"),
                ("guion-en", "en", ["nombre"], [], "avatar"), ("guion-fideicomiso", "es", [], [], "avatar")]
cases_drafter = [("will", 1, None), ("will", 1, 6), ("will", 7, 12), ("trust", 1, 5), ("ahcd", 1, None)]
out = {"system_prompt": [{"args": list(c), "text": s.system_prompt(*c)} for c in cases_prompt],
       "drafter": [{"args": list(c), "text": s.drafter(*c)} for c in cases_drafter],
       "spoken": [{"in": x, "out": s.spoken(x)} for x in ["Who is the guardian? Also, what state? [FIN]", "Le dejo 5.000 dólares a St. Andrew. ¿Algo más?"]],
       "verified_keys": sorted(s.VERIFIED), "docs_keys": list(s.DOCS)}
json.dump(out, open("tests/fixtures/carbon_intake_snapshots.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("snapshots:", {k: len(v) for k, v in out.items()})
