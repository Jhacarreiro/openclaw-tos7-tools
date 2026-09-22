#!/usr/bin/env python3
import pathlib,re,sys
R=pathlib.Path(__file__).resolve().parents[1];S={".git","node_modules","dist","__pycache__"}
P={"private IPv4":re.compile(r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"),"private hostname":re.compile(r"\bGallivanter\b",re.I),"private path":re.compile(r"/data/\.openclaw|/home/[^/\s]+/\.docker/openclaw")}
B=[]
for p in R.rglob("*"):
 if not p.is_file() or any(x in S for x in p.parts):continue
 try:t=p.read_text(errors="replace")
 except OSError:continue
 for l,r in P.items():
  for m in r.finditer(t):B.append((p.relative_to(R),l,m.group(0)))
if B:
 [print(f"FAIL {p}: {l}: {v}") for p,l,v in B];sys.exit(1)
print("Public audit OK.")
