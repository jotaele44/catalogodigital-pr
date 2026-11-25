"""Bounded candidate semantics. Not a publication authorization engine."""
import re
from datetime import date

def coarse_bounds(value, precision):
    patterns={"YEAR":r"[0-9]{4}","MONTH":r"[0-9]{4}-[0-9]{2}","DAY":r"[0-9]{4}-[0-9]{2}-[0-9]{2}"}
    if precision not in patterns or not isinstance(value,str) or not re.fullmatch(patterns[precision],value):
        raise ValueError("invalid calendar precision")
    parts=list(map(int,value.split("-")))
    y=parts[0]; m=parts[1] if len(parts)>1 else 1; d=parts[2] if len(parts)>2 else 1
    start=date(y,m,d)
    if precision=="YEAR": end=date(y+1,1,1)
    elif precision=="MONTH": end=date(y+1,1,1) if m==12 else date(y,m+1,1)
    else: end=date.fromordinal(start.toordinal()+1)
    return start.isoformat(),end.isoformat()

def membership(subject_ids, facet_claims, taxonomy, profiles):
    """Candidate matches only; broad domain inclusion is not qualified membership."""
    nodes={x["id"]:x for x in taxonomy["domains"]+taxonomy["subjects"]}
    if any(x not in nodes for x in subject_ids): raise ValueError("unknown subject")
    domains=set()
    for code in subject_ids:
        item=nodes[code]
        if code.startswith("U"): domains.add(code)
        domains.update(item.get("parents",[]))
        domains.update(item.get("related_domains",[]))
    allowed={p["facet"] for p in profiles if p.get("facet")}
    if not set(facet_claims)<=allowed: raise ValueError("unknown facet")
    return sorted(p["id"] for p in profiles if (p.get("facet") in facet_claims if p.get("facet") else bool(domains.intersection(p["domains"]))))

def geographic_candidate(namespace, native_id, release, receipt):
    """No authority verification implied; binding must retain source provenance."""
    if not all(isinstance(x,str) and x.strip() for x in (namespace,native_id,release,receipt)):
        raise ValueError("incomplete geographic identity")
    if namespace=="US_CENSUS_COUNTY_GEOID" and not re.fullmatch(r"72[0-9]{3}",native_id):
        raise ValueError("not a Puerto Rico county-equivalent GEOID shape")
    return {"namespace":namespace,"native_id":native_id,"release":release,"receipt":receipt,"status":"CANDIDATE"}
