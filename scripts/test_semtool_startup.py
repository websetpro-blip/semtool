#!/usr/bin/env python
"""Test KeySet startup to find where it hangs"""
import sys
print("1. Starting test...")

print("2. Importing PySide6...")
from PySide6.QtWidgets import QApplication
print("   OK")

print("3. Importing keyset.core.db...")
from keyset.core.db import Base, engine, ensure_schema, SessionLocal
print("   OK")

print("4. Ensuring schema...")
ensure_schema()
print("   OK")

print("5. Testing DB session...")
with SessionLocal() as session:
    print(f"   Session created: {session}")
print("   OK")

print("6. Importing main module...")
from keyset.app.main import MainWindow
print("   OK")

print("7. Creating QApplication...")
app = QApplication(sys.argv)
print("   OK")

print("8. Creating MainWindow...")
window = MainWindow()
print("   OK")

print("\n✅ ALL TESTS PASSED - KeySet should start normally")
print("If it hangs after this, the problem is in window.show() or app.exec()")
