import argparse,json,tempfile
from .integration import Harness,seed_demo
def demo(a):
    with tempfile.TemporaryDirectory() as td: print(json.dumps(seed_demo(td),indent=2))
def build(a):
    h=Harness(a.db,a.out); p=h.build(a.idea); print(json.dumps({"project":p,"verify":h.verify(p["project"])},indent=2))
def main():
    p=argparse.ArgumentParser(); p.add_argument("--db",default="integration.db"); p.add_argument("--out",default="generated_app")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=demo)
    b=sub.add_parser("build"); b.add_argument("idea"); b.set_defaults(func=build)
    sub.add_parser("stats").set_defaults(func=lambda a: print(json.dumps(Harness(a.db,a.out).stats(),indent=2)))
    e=sub.add_parser("export"); e.add_argument("output"); e.set_defaults(func=lambda a: print(json.dumps(Harness(a.db,a.out).export(a.output),indent=2)))
    a=p.parse_args(); a.func(a)
if __name__=="__main__": main()
