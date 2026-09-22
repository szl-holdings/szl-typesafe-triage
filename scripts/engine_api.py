import importlib, inspect, json, pkgutil, sys
from pathlib import Path
sys.path.insert(0, "src")

import szl_triage
mods = {}
for m in pkgutil.iter_modules(szl_triage.__path__):
    try:
        mods[m.name] = importlib.import_module("szl_triage." + m.name)
    except Exception as e:
        print("IMPORT FAIL", m.name, type(e).__name__, e)

print("=== PUBLIC CALLABLES ===")
api = {}
for name, mod in sorted(mods.items()):
    for fn_name, fn in vars(mod).items():
        if fn_name.startswith("_"):
            continue
        if inspect.isfunction(fn) and fn.__module__ == mod.__name__:
            sig = str(inspect.signature(fn))
            api[name + "." + fn_name] = sig
            print("  " + (name + "." + fn_name).ljust(38) + sig)
        elif inspect.isclass(fn) and fn.__module__ == mod.__name__:
            try:
                print("  class " + (name + "." + fn_name).ljust(32) + str(inspect.signature(fn.__init__)))
            except Exception:
                print("  class " + name + "." + fn_name)

Path("out/engine_api.json").write_text(json.dumps(api, indent=2), encoding="utf-8")
print("")
print("RECEIPT out/engine_api.json")

print("")
print("=== POLICY LOADERS ===")
for k, v in api.items():
    if any(w in k.lower() for w in ("load", "policy", "from_")):
        print("  " + k + " " + v)
print("")
print("=== DECISION ENTRY POINTS ===")
for k, v in api.items():
    if any(w in k.lower() for w in ("decide", "triage", "classif", "evaluat", "disposition", "aggregate", "run")):
        print("  " + k + " " + v)