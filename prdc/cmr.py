"""Bounded NASA CMR collection metadata acquisition; never publishes records."""
import json
import re
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPRedirectHandler, Request
from datetime import datetime, timezone
import hashlib

BASE='https://cmr.earthdata.nasa.gov/search/collections.umm_json'
MAX_BYTES=8*1024*1024

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

def fetch_page(query='Puerto Rico',page=1,page_size=10):
    if not isinstance(query,str) or not query.strip() or len(query)>100: raise ValueError('bounded query required')
    if type(page) is not int or not 1<=page<=5 or type(page_size) is not int or not 1<=page_size<=20: raise ValueError('bounded page required')
    url=BASE+'?'+urlencode({'keyword':query,'page_num':page,'page_size':page_size,'sort_key':'concept_id'})
    opener=build_opener(NoRedirect())
    with opener.open(Request(url,headers={'Accept':'application/json','User-Agent':'PRDC-reference/0.1'}),timeout=20) as r:
        if r.status!=200 or r.geturl()!=url: raise ValueError('unexpected response')
        raw=r.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES: raise ValueError('response exceeds bound')
        hits=r.headers.get('CMR-Hits')
    return raw, {'url':url,'observed_at':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(raw).hexdigest(),'byte_count':len(raw),'cmr_hits':hits,'page':page,'page_size':page_size}

def parse_page(raw):
    body=json.loads(raw)
    items=body.get('items') if isinstance(body,dict) else None
    if not isinstance(items,list): raise ValueError('invalid CMR items')
    seen=set(); result=[]
    for item in items:
        m=item['meta']; u=item['umm']
        cid=m['concept-id']; rev=m['revision-id']
        if not isinstance(cid,str) or not re.fullmatch(r'C[0-9]+-[A-Za-z0-9_]+',cid) or type(rev) is not int or rev<1: raise ValueError('invalid native identity')
        if cid in seen: raise ValueError('duplicate collection identity')
        seen.add(cid)
        title=u['EntryTitle']
        if not isinstance(title,str) or not title.strip(): raise ValueError('missing title')
        result.append({'concept_id':cid,'revision_id':rev,'title':title,'geographic_applicability':'UNVERIFIED'})
    return result

def reconcile(pages):
    """Bounded page accounting; never claims a stable catalog snapshot."""
    ids=set(); counts=set(); expected=1
    for raw,receipt in pages:
        if receipt['page']!=expected: raise ValueError('noncontiguous pages')
        if hashlib.sha256(raw).hexdigest()!=receipt['sha256'] or len(raw)!=receipt['byte_count']: raise ValueError('receipt mismatch')
        rows=parse_page(raw)
        if len(rows)>receipt['page_size']: raise ValueError('page exceeds bound')
        if any(x['concept_id'] in ids for x in rows): raise ValueError('duplicate across pages')
        ids.update(x['concept_id'] for x in rows)
        counts.add(receipt['cmr_hits']); expected+=1
    total=None
    if len(counts)==1:
        value=next(iter(counts))
        if isinstance(value,str) and value.isdecimal(): total=int(value)
    if total is not None and len(ids)>total: raise ValueError('inconsistent hit count')
    return {'retrieved':len(ids),'reported_hits':total,'state':'COUNT_MATCH_ONLY' if total is not None and len(ids)==total else 'PARTIAL','certified':False}
