"""
Compatibility shim: keep old SemTool entry point by delegating to KeySet.
"""
from run_keyset import _bootstrap


if __name__ == "__main__":
    _bootstrap()
