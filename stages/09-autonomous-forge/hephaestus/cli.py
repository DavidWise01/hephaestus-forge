import argparse,json,tempfile
from .autonomous import AutoForge,seed_demo
def demo(a):
    with tempfile.TemporaryDirectory() as td: print(json.dumps(seed_demo(td),indent=2))
def main():
    p=argparse.ArgumentParser(); p.add_argument("--db",default="auto.db"); p.add_argument("--out",default="generated_system")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=demo)
    b=sub.add_parser("build"); b.add_argument("request"); b.set_defaults(func=lambda a: print(json.dumps(AutoForge(a.db,a.out).build(a.request),indent=2)))
    sub.add_parser("stats").set_defaults(func=lambda a: print(json.dumps(AutoForge(a.db,a.out).stats(),indent=2)))
    e=sub.add_parser("export"); e.add_argument("output"); e.set_defaults(func=lambda a: print(json.dumps(AutoForge(a.db,a.out).export(a.output),indent=2)))
    a=p.parse_args(); a.func(a)
if __name__=="__main__": main()
