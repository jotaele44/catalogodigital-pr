"""Replay bounded synthetic candidate contract fixtures, not live source qualification."""
import json, sys
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent / "baselines" / "prdc-r2"))
from prdc import valid_candidate_url
schema = json.loads((here / "candidate.schema.json").read_text())
cases = json.loads((here / "candidate-fixtures.json").read_text())
Draft202012Validator.check_schema(schema)
v = Draft202012Validator(schema, format_checker=FormatChecker())
results = []
for c in cases:
    r = c["record"]
    ok = v.is_valid(r)
    if r.get("url") is not None:
        ok = ok and bool(valid_candidate_url(r["url"]))
    if "parent" in r:
        ok = ok and r["parent"] != r["child"]
    results.append(dict(name=c["name"], expected=c["valid"], actual=ok, **{"pass": ok == c["valid"]}))
expected = json.loads((here / "qualification-results.json").read_text())
assert results == expected and all(x["pass"] for x in results)
print(f"{len(results)}/{len(results)} bounded fixtures passed")
