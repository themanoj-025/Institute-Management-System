"""
Comprehensive Import Audit
Walks every .py file in the project (excluding __pycache__ and venv),
checks for syntax validity, then attempts to import each module.
"""

import importlib
import os
import sys
from typing import TypedDict

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

EXCLUDE_DIRS = {"__pycache__", "venv", ".git", ".github"}


def get_project_files() -> list[object]:
    """Get all .py files in the project excluding excluded dirs."""
    files = []
    for root, dirs, fnames in os.walk(PROJECT_ROOT):
        # Prune excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in fnames:
            if f.endswith(".py"):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, PROJECT_ROOT)
                files.append((rel_path, full_path))
    return sorted(files)


def compute_module_name(rel_path) -> str:
    """Convert a relative file path like 'services/auth_service.py' to 'services.auth_service'."""
    parts = rel_path.replace("\\", "/").split("/")
    mod_name = parts[-1].replace(".py", "")
    if mod_name == "__init__":
        mod_name = ""
    # Build dotted module path
    pkg_parts = parts[:-1] + ([mod_name] if mod_name else [])
    return ".".join(pkg_parts)


def safe_py_compile(filepath) -> tuple[object, ...]:
    """Try to compile a .py file and return (success, error_msg)."""
    try:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()
        compile(source, filepath, "exec")
        return True, None
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"
    except (OSError, ValueError) as e:
        return False, f"CompileError: {e}"


class AuditResults(TypedDict):
    compile_ok: int
    compile_fail: list[tuple[str, str | None]]
    import_ok: int
    import_fail: list[tuple[str, str, str]]
    bypass_import: list[tuple[str, str, str]]

results: AuditResults = {
    "compile_ok": 0,
    "compile_fail": [],
    "import_ok": 0,
    "import_fail": [],
    "bypass_import": [],
}

print("=" * 70)
print("COMPREHENSIVE IMPORT AUDIT")
print("=" * 70)

files = get_project_files()
print(f"\nFound {len(files)} .py files to audit\n")

for rel_path, full_path in files:
    mod_name = compute_module_name(rel_path)

    # --- Step 1: Syntax check ---
    ok, err = safe_py_compile(full_path)
    if not ok:
        results["compile_fail"].append((rel_path, err))
        print(f"  [COMPILE FAIL] {rel_path}: {err}")
        continue
    results["compile_ok"] += 1

    # --- Step 2: Try to import the module ---
    # Skip modules that require Tkinter root window, matplotlib backend, etc.
    # These can only be tested within the running app.
    bypass_keywords = ["ui.", "modules.", "landing.", "main.py"]
    should_bypass = any(rel_path.startswith(k) or rel_path == k for k in bypass_keywords)

    if should_bypass:
        # Still try to verify the module path structure is valid
        # by checking that the parent package exists
        parent = ".".join(mod_name.split(".")[:-1]) if "." in mod_name else ""
        if parent:
            try:
                importlib.import_module(parent)
                results["bypass_import"].append(
                    (rel_path, mod_name, "OK (parent valid)")
                )
            except ImportError as e:
                results["import_fail"].append(
                    (rel_path, mod_name, f"Parent import failed: {e}")
                )
        else:
            results["bypass_import"].append(
                (rel_path, mod_name, "OK (SKIP - needs Tk)")
            )
        continue

    try:
        importlib.import_module(mod_name)
        results["import_ok"] += 1
    except ImportError as e:
        results["import_fail"].append((rel_path, mod_name, str(e)))
    except (OSError, ValueError, AttributeError) as e:
        results["import_fail"].append((rel_path, mod_name, f"{type(e).__name__}: {e}"))

# --- Summary ---
print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"\nTotal files checked: {len(files)}")
print(f"  Syntax OK:          {results['compile_ok']}")
print(f"  Syntax FAILED:      {len(results['compile_fail'])}")
print(f"  Imported OK:        {results['import_ok']}")
print(f"  Bypassed (Tk/UI):   {len(results['bypass_import'])}")
print(f"  Import FAILED:      {len(results['import_fail'])}")

if results["compile_fail"]:
    print("\n--- SYNTAX ERRORS ---")
    for path, err in results["compile_fail"]:
        print(f"  {path}: {err}")

if results["import_fail"]:
    print("\n--- IMPORT ERRORS ---")
    for path, mod, err in results["import_fail"]:
        print(f"  {path} ({mod}): {err}")

if results["bypass_import"]:
    print("\n--- BYPASSED (needs Tkinter runtime) ---")
    for path, mod, reason in results["bypass_import"]:
        print(f"  {path} ({mod}): {reason}")

# Overall status
if not results["compile_fail"] and not results["import_fail"]:
    print("\n[PASS] No syntax or import errors found!")
else:
    print(
        f"\n[WARN] {len(results['compile_fail'])} syntax error(s), {len(results['import_fail'])} import error(s)"
    )
