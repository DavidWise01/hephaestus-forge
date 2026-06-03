import argparse,json,tempfile
from .codegen import CodeGen,seed_demo
def demo(a):
    with tempfile.TemporaryDirectory() as td: print(json.dumps(seed_demo(td),indent=2))
def main():
    p=argparse.ArgumentParser(); p.add_argument("--db",default="codegen.db"); p.add_argument("--out",default="generated")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=demo)
    g=sub.add_parser("generate"); g.add_argument("idea"); g.set_defaults(func=lambda a: print(json.dumps(CodeGen(a.db,a.out).gen(a.idea),indent=2)))
    sub.add_parser("stats").set_defaults(func=lambda a: print(json.dumps(CodeGen(a.db,a.out).stats(),indent=2)))
    e=sub.add_parser("export"); e.add_argument("output"); e.set_defaults(func=lambda a: print(json.dumps(CodeGen(a.db,a.out).export(a.output),indent=2)))
    a=p.parse_args(); a.func(a)
if __name__=="__main__": main()
