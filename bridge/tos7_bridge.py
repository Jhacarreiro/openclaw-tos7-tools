#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,pathlib,re,subprocess,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
SAFE=re.compile(r"^[A-Za-z0-9_. -]{1,128}$")
def run(a,t=8):
 try:r=subprocess.run(a,capture_output=True,text=True,timeout=t,check=False,env=os.environ.copy())
 except FileNotFoundError:return {"ok":False,"error":"command_not_found","command":a[0]}
 except subprocess.TimeoutExpired:return {"ok":False,"error":"timeout","command":a[0]}
 out=r.stdout[:2000000]; data=None
 if out.strip():
  try:data=json.loads(out)
  except json.JSONDecodeError:data=out.rstrip()
 return {"ok":r.returncode==0,"exit_code":r.returncode,"data":data,"stderr":r.stderr[:2000000].rstrip() or None}
def tos(*a):return run(["/usr/bin/tos",*a,"--json"])
def text(p):
 try:return pathlib.Path(p).read_text().strip()
 except OSError:return None
def name(v):
 if not isinstance(v,str) or not SAFE.fullmatch(v):raise ValueError("invalid_name")
 return v
def metrics():
 o={"source":["/proc/loadavg","/proc/meminfo","/proc/uptime"]}; l=text("/proc/loadavg")
 if l:
  p=l.split();o.update(load_1m=float(p[0]),load_5m=float(p[1]),load_15m=float(p[2]),processes=p[3])
 u=text("/proc/uptime")
 if u:o["uptime_seconds"]=float(u.split()[0])
 m=text("/proc/meminfo")
 if m:
  v={}
  for x in m.splitlines():
   k,_,z=x.partition(":")
   try:v[k]=int(z.strip().split()[0])*1024
   except:pass
  for k in ("MemTotal","MemAvailable","MemFree","SwapTotal","SwapFree"):
   if k in v:o[k.lower()+"_bytes"]=v[k]
 return o
def temps():
 out=[]
 for h in pathlib.Path("/sys/class/hwmon").glob("hwmon*"):
  chip=text(str(h/"name")) or h.name
  for f in h.glob("temp*_input"):
   try:c=int(f.read_text().strip())/1000
   except:continue
   out.append({"chip":chip,"label":text(str(f).replace("_input","_label")) or f.stem,"celsius":c,"source":"sysfs"})
 return out
def ups():
 d=run(["upsc","-l"])
 if not d["ok"] or not isinstance(d["data"],str):return {"configured":False,"raw":d}
 rows=[]
 for n in [x.strip() for x in d["data"].splitlines() if x.strip()]:
  r=run(["upsc",n]);vals={}
  if r["ok"] and isinstance(r["data"],str):
   for x in r["data"].splitlines():
    k,s,v=x.partition(":")
    if s:vals[k.strip()]=v.strip()
  raw=(r.get("stderr") or "")+" "+str(r.get("data") or "")
  rows.append({"name":n,"ok":r["ok"],"stale":"Data stale" in raw,"values":vals,"error":None if r["ok"] else raw.strip()})
 return {"configured":bool(rows),"devices":rows,"source":"NUT/upsc"}
def net():
 raw=text("/proc/net/dev") or "";o={}
 for x in raw.splitlines()[2:]:
  if ":" not in x:continue
  i,d=x.split(":",1);p=d.split()
  if len(p)>=16:o[i.strip()]={"rx_bytes":int(p[0]),"rx_packets":int(p[1]),"tx_bytes":int(p[8]),"tx_packets":int(p[9])}
 return {"interfaces":o,"source":"/proc/net/dev"}
def docker(n=None):
 ids=run(["docker","ps","-aq"]+(["--filter",f"name={n}"] if n else []))
 if not ids["ok"] or not isinstance(ids["data"],str):return ids
 fmt="{{.Name}}|{{.State.Status}}|{{.State.ExitCode}}|{{.RestartCount}}|{{.State.OOMKilled}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}|{{.HostConfig.RestartPolicy.Name}}|{{.Config.Image}}";rows=[]
 for cid in [x for x in ids["data"].splitlines() if x.strip()]:
  r=run(["docker","inspect",cid,"--format",fmt])
  if not r["ok"] or not isinstance(r["data"],str):rows.append({"id":cid,"error":r});continue
  p=r["data"].split("|",7);rows.append({"name":p[0].lstrip("/"),"status":p[1],"exit_code":int(p[2]),"restart_count":int(p[3]),"oom_killed":p[4].lower()=="true","health":p[5],"restart_policy":p[6],"image":p[7]})
 return {"ok":True,"containers":rows,"source":"docker inspect"}
def system(_):return {"tos":tos("info"),"metrics":metrics(),"temperatures":temps()}
def power(_):return {"fan":tos("fan","status"),"buzzer":tos("buzzer","status"),"ups":ups()}
def storage(p):
 s=p.get("section","overview");m={"overview":("storage","info"),"disks":("disk","list","--detail"),"arrays":("array","list","--detail"),"volumes":("volume","list","--detail")}
 if s not in m:raise ValueError("invalid_section")
 return {"section":s,"result":tos(*m[s])}
def services(_):return {"services":tos("service","list"),"file_services":tos("fileservice","status"),"ssh":tos("ssh","status"),"failed_units":run(["systemctl","--failed","--no-legend","--no-pager"])}
def apps(p):
 n=p.get("name");return {"apps":tos("app","list")} if n is None else {"info":tos("app","info",name(n)),"status":tos("app","status",name(n))}
def users(p):
 s=p.get("section","users");m={"users":("user","list"),"groups":("user-group","list","--detail"),"online":("user","online")}
 if s not in m:raise ValueError("invalid_section")
 return {"section":s,"result":tos(*m[s])}
def shares(p):
 n=p.get("name");return {"shares":tos("shared-folder","list","--detail")} if n is None else {"share":tos("shared-folder","show",name(n))}
def security(p):
 o={"firewall":tos("firewall","status"),"rules":tos("firewall","rule","--detail")}
 if p.get("includeListeners"):o["listeners"]=run(["ss","-lntuH"])
 return o
def logs(p):
 a=["log","view"]
 if p.get("category"):a+=["--category",name(p["category"])]
 if p.get("level"):a+=["--level",name(p["level"])]
 lim=int(p.get("limit",100))
 if not 1<=lim<=200:raise ValueError("invalid_limit")
 return {"logs":tos(*a,"--limit",str(lim))}
def health(_):
 d=docker();r=d.get("containers",[]) if d.get("ok") else []
 return {"generated_at":int(time.time()),"system":system({}),"power":power({}),"storage":storage({"section":"overview"}),"services":services({}),"docker_summary":{"total":len(r),"unhealthy":[x["name"] for x in r if x.get("health")=="unhealthy"],"restarting":[x["name"] for x in r if x.get("status")=="restarting"],"oom_killed":[x["name"] for x in r if x.get("oom_killed")]}}
A={"system":system,"power":power,"storage":storage,"network":lambda _:{"tos":tos("network","info"),"counters":net()},"services":services,"apps":apps,"users":users,"shares":shares,"security":security,"logs":logs,"docker":lambda p:docker(name(p["name"]) if p.get("name") is not None else None),"health_snapshot":health}
class H(BaseHTTPRequestHandler):
 def sendj(self,c,p):
  b=json.dumps(p,separators=(",",":"),default=str).encode();self.send_response(c);self.send_header("content-type","application/json");self.send_header("content-length",str(len(b)));self.end_headers();self.wfile.write(b)
 def do_GET(self):self.sendj(200,{"ok":True,"actions":sorted(A)}) if self.path=="/health" else self.sendj(404,{"error":"not_found"})
 def do_POST(self):
  if self.path!="/v1/query":return self.sendj(404,{"error":"not_found"})
  t=getattr(self.server,"bridge_token","")
  if t and self.headers.get("authorization")!=f"Bearer {t}":return self.sendj(401,{"error":"unauthorized"})
  try:
   n=int(self.headers.get("content-length","0"))
   if n<=0 or n>65536:raise ValueError("invalid_body_size")
   q=json.loads(self.rfile.read(n));a=q.get("action");p=q.get("params") or {}
   if a not in A or not isinstance(p,dict):raise ValueError("invalid_action_or_params")
   self.sendj(200,{"ok":True,"action":a,"result":A[a](p)})
  except (ValueError,json.JSONDecodeError) as e:self.sendj(400,{"ok":False,"error":str(e)})
  except Exception as e:self.sendj(500,{"ok":False,"error":type(e).__name__})
 def log_message(self,f,*a):pass
def main():
 p=argparse.ArgumentParser();p.add_argument("--listen",default="127.0.0.1");p.add_argument("--port",type=int,default=5077);x=p.parse_args();t=os.getenv("TOS7_BRIDGE_TOKEN","")
 if x.listen not in ("127.0.0.1","::1","localhost") and not t:raise SystemExit("Refusing non-loopback bind without TOS7_BRIDGE_TOKEN")
 s=ThreadingHTTPServer((x.listen,x.port),H);s.bridge_token=t;print(f"tos7-bridge listening on {x.listen}:{x.port}");s.serve_forever()
if __name__=="__main__":main()
