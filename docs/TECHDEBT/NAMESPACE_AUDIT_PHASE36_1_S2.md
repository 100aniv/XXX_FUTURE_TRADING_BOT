# Namespace Audit - PHASE36-1 Step 2

**Date**: 2025-12-24  
**Scope**: Project-wide namespace duplication detection  
**Purpose**: Prevent new singular/plural conflicts & import shadowing

---

## 🔍 Audit Results

### 1. Detected Conflicts (Singular/Plural)

| Singular | Plural | Status | Risk Level |
|----------|--------|--------|------------|
| `config/` | `configs/` | ⚠️ BOTH EXIST | MEDIUM (import confusion) |
| `db/` | `database/` | ⚠️ BOTH EXIST | MEDIUM (path ambiguity) |
| - | `common/database/` | ⚠️ SHIM LAYER | LOW (intentional compat) |

### 2. Import Analysis

**Legacy `common.database` usage**:
- SHIM created: `common/database/__init__.py` → `database.postgres`
- Purpose: Backward compatibility for existing imports
- **Action**: ✅ SHIM implemented (PHASE36-1 S2)
- **Recommendation**: Migrate to `from database.postgres import ...` in new code

**Config namespace**:
- `config/` (old, mostly empty)
- `configs/` (active, 12k+ files)
- **Risk**: Accidental import from wrong location
- **Recommendation**: Remove `config/` in future PHASE (requires large refactor)

**DB namespace**:
- `db/` (schema/init scripts)
- `database/` (Python modules: postgres.py)
- `common/database/` (SHIM only)
- **Risk**: Import path confusion
- **Current state**: Manageable with SHIM

---

## 🚨 New Namespace Gate Rules

### Preflight Check (Add to preflight script)

```python
# scripts/phase36/preflight_phase36_0.py

FORBIDDEN_NEW_IMPORTS = [
    "from common.database import",  # Use database.postgres instead
]

FORBIDDEN_NEW_FOLDERS = [
    "common/db",
    "common/configs",
    "data/database",
]

def check_namespace_violations(changed_files):
    """Scan for forbidden namespace patterns in new/modified files"""
    violations = []
    for file in changed_files:
        content = read_file(file)
        for pattern in FORBIDDEN_NEW_IMPORTS:
            if pattern in content and is_new_usage(file, pattern):
                violations.append(f"{file}: {pattern}")
    
    if violations:
        raise PreflightError(f"Namespace violations: {violations}")
```

---

## 📋 Tech Debt Items

### TD-1: Config Consolidation
- **Issue**: `config/` and `configs/` both exist
- **Impact**: Import confusion, scattered config files
- **Effort**: MEDIUM (requires file migration + import updates)
- **Priority**: P2 (not urgent, but should address)
- **Proposed PHASE**: PHASE37 or dedicated refactor PHASE

### TD-2: Database Path Unification
- **Issue**: `db/`, `database/`, `common/database/` overlap
- **Impact**: Path ambiguity
- **Current mitigation**: SHIM layer working
- **Effort**: LOW (mostly documentation)
- **Priority**: P3 (maintain status quo with SHIM)

### TD-3: Namespace Audit Tool
- **Issue**: No automated detection of new conflicts
- **Solution**: Add preflight gate (see above)
- **Effort**: LOW (2-3 hours)
- **Priority**: P1 (prevent regression)
- **Target**: PHASE36-1 S3 or S4

---

## ✅ S2 Actions Taken

1. ✅ Created `common/database/__init__.py` SHIM
2. ✅ Documented existing conflicts
3. ✅ Defined gate rules for preflight
4. ⏸️ Preflight gate implementation (deferred to avoid scope creep)

---

## 🎯 Recommendations

### Short-term (PHASE36-1)
- ✅ SHIM layer sufficient for S2
- ⏸️ Add namespace gate to preflight (optional, low priority)

### Mid-term (PHASE37-38)
- Consolidate `config/` → `configs/` (or vice versa)
- Document "official" import paths in README

### Long-term (PHASE40+)
- Consider project-wide import audit tool
- Enforce singular naming convention (configs → config, strategies → strategy)

---

**Audit Status**: ✅ COMPLETE  
**Gate Status**: ⏸️ DEFERRED (rules defined, implementation optional)  
**Blocker**: None (SHIM resolves immediate issues)
