
import argparse, json, tempfile
from .assembly import AssemblyLine, seed_demo
def demo(a):
    with tempfile.TemporaryDirectory() as td: print(json.dumps(seed_demo(td), indent=2))
def enqueue(a): print(json.dumps(AssemblyLine(a.db,a.out,a.releases).enqueue(a.idea), indent=2))
def run(a): print(json.dumps(AssemblyLine(a.db,a.out,a.releases).run_all(), indent=2))
def dashboard(a): print(json.dumps(AssemblyLine(a.db,a.out,a.releases).dashboard(), indent=2))
def export(a): print(json.dumps(AssemblyLine(a.db,a.out,a.releases).export(a.output), indent=2))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="assembly.db"); p.add_argument("--out",default="artifacts"); p.add_argument("--releases",default="releases")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=demo)
    e=sub.add_parser("enqueue"); e.add_argument("idea"); e.set_defaults(func=enqueue)
    sub.add_parser("run").set_defaults(func=run)
    sub.add_parser("dashboard").set_defaults(func=dashboard)
    x=sub.add_parser("export"); x.add_argument("output"); x.set_defaults(func=export)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": main()
