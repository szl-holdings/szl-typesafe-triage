import sys, torch, transformers
print("python      :", sys.version.split()[0])
print("torch       :", torch.__version__)
print("transformers:", transformers.__version__)
print("arch_list   :", torch.cuda.get_arch_list())
print("capability  :", torch.cuda.get_device_capability(0) if torch.cuda.is_available() else "no device")
assert "sm_120" in torch.cuda.get_arch_list(), "wheel lacks sm_120 kernels"