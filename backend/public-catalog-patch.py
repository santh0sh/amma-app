from pathlib import Path
import hashlib
p=Path('backend/stories.py')
s=p.read_text()
assert hashlib.sha256(s.encode()).hexdigest()=='c6c0f2bb49ae70aad63b8c9c24deb2465dbc1cc41a1816edd06265e834258dc2'
old='''    for w in works:
        w["first_seen"] = seen.get(w["id"], "2000-01-01" if first_run else day)
        if not w.get("readable"):
            w.pop("parts", None)

'''
assert s.count(old)==1
new=Path('backend/backend/public-catalog-block.txt').read_text()
out=s.replace(old,new)
assert hashlib.sha256(out.encode()).hexdigest()=='d2725d14d267426aa50aff5545bd620b40d28f5f17ae02e5d720e3673ff18c54'
p.write_text(out)
