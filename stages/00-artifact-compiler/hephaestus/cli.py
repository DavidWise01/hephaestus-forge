
import argparse,json,tempfile
from .forge import Forge,seed_demo
def demo(a):
    with tempfile.TemporaryDirectory() as td: print(json.dumps(seed_demo(td),indent=2))
def compile_cmd(a): print(json.dumps(Forge(a.db,a.out).compile(a.idea,a.name,a.parent),indent=2))
def dashboard(a): print(json.dumps(Forge(a.db,a.out).dashboard(),indent=2))
def export(a): print(json.dumps(Forge(a.db,a.out).export(a.output),indent=2))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="hephaestus.db"); p.add_argument("--out",default="artifacts")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=demo)
    c=sub.add_parser("compile"); c.add_argument("idea"); c.add_argument("--name"); c.add_argument("--parent",default=""); c.set_defaults(func=compile_cmd)
    sub.add_parser("dashboard").set_defaults(func=dashboard)
    e=sub.add_parser("export"); e.add_argument("output"); e.set_defaults(func=export)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": main()
