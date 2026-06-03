import argparse,json,tempfile
from .intelligence import ForgeIntelligence,seed_demo
def demo(a):
    with tempfile.TemporaryDirectory() as td: print(json.dumps(seed_demo(td),indent=2))
def main():
    p=argparse.ArgumentParser(); p.add_argument("--db",default="forge_intelligence.db"); p.add_argument("--artifacts",default="artifacts"); p.add_argument("--releases",default="releases"); p.add_argument("--plans",default="plans")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=demo)
    pl=sub.add_parser("plan"); pl.add_argument("idea"); pl.set_defaults(func=lambda a: print(json.dumps(ForgeIntelligence(a.db,a.artifacts,a.releases,a.plans).plan(a.idea),indent=2)))
    b=sub.add_parser("build"); b.add_argument("idea"); b.set_defaults(func=lambda a: print(json.dumps(ForgeIntelligence(a.db,a.artifacts,a.releases,a.plans).build_system(a.idea),indent=2)))
    sub.add_parser("dashboard").set_defaults(func=lambda a: print(json.dumps(ForgeIntelligence(a.db,a.artifacts,a.releases,a.plans).dashboard(),indent=2)))
    e=sub.add_parser("export"); e.add_argument("output"); e.set_defaults(func=lambda a: print(json.dumps(ForgeIntelligence(a.db,a.artifacts,a.releases,a.plans).export(a.output),indent=2)))
    a=p.parse_args(); a.func(a)
if __name__=="__main__": main()
