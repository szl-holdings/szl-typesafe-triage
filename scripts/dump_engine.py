import inspect, sys
sys.path.insert(0, "src")
from szl_triage import axes, pipeline
print("=== axes.py ===")
print(inspect.getsource(axes))
print("=== pipeline.decide ===")
print(inspect.getsource(pipeline.decide))