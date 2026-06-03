import argparse,json,tempfile
from .graph import Graph,seed_demo
def demo(a):
    with tempfile.TemporaryDirectory() as td: print(json.dumps(seed_demo(td),indent=2))
def main():
    p=argparse.ArgumentParser(); p.add_argument("--db",default="graph.db"); p.add_argument("--out",default="artifacts")
    sub=p.add_subparsers(dest="cmd",required=True); sub.add_parser("demo").set_defaults(func=demo)
    c=sub.add_parser("compile"); c.add_argument("idea"); c.add_argument("--name"); c.set_defaults(func=lambda a: print(json.dumps(Graph(a.db,a.out).compile(a.idea,a.name),indent=2)))
    l=sub.add_parser("link"); l.add_argument("src"); l.add_argument("dst"); l.add_argument("--relation",default="depends_on"); l.set_defaults(func=lambda a: print(json.dumps(Graph(a.db,a.out).link(a.src,a.dst,a.relation),indent=2)))
    sub.add_parser("graph").set_defaults(func=lambda a: print(json.dumps(Graph(a.db,a.out).graph(),indent=2)))
    sub.add_parser("verify").set_defaults(func=lambda a: print(json.dumps(Graph(a.db,a.out).verify_graph(),indent=2)))
    e=sub.add_parser("export"); e.add_argument("output"); e.set_defaults(func=lambda a: print(json.dumps(Graph(a.db,a.out).export(a.output),indent=2)))
    a=p.parse_args(); a.func(a)
if __name__=="__main__": main()
