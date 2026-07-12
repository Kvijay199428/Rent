import os
import re
import sys

# Define directories to scan
DIRECTORIES = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "app")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend")),
]

# Exclude these files (the manifest generators and manifests themselves)
EXCLUDE_FILES = [
    "routes.json",
    "routes_manifest.py",
    "routes.ts",
    "gen_routes.py",
    "replace_routes.py",
    "validate_routes.py"
]

# Patterns to look for
PATTERNS = [
    r'(?<![A-Za-z0-9_])"/admin/api/[a-zA-Z0-9_/-]+"?',
    r"(?<![A-Za-z0-9_])'/admin/api/[a-zA-Z0-9_/-]+'?",
    r"(?<![A-Za-z0-9_])`/admin/api/[a-zA-Z0-9_/-]+`?",
    r'(?<![A-Za-z0-9_])"/api/[a-zA-Z0-9_/-]+"?',
    r"(?<![A-Za-z0-9_])'/api/[a-zA-Z0-9_/-]+'?",
    r"(?<![A-Za-z0-9_])`/api/[a-zA-Z0-9_/-]+`?",
]

def scan_files():
    found_issues = []
    
    for directory in DIRECTORIES:
        for root, dirs, files in os.walk(directory):
            if "node_modules" in dirs:
                dirs.remove("node_modules")
            for file in files:
                if any(file.endswith(ext) for ext in [".py", ".ts", ".tsx"]):
                    if file in EXCLUDE_FILES:
                        continue
                        
                    file_path = os.path.join(root, file)
                    
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                            
                        for i, line in enumerate(lines):
                            # Check each pattern
                            for pattern in PATTERNS:
                                matches = re.findall(pattern, line)
                                # Filter out any matches that are just "/api/" or "/admin/api/" without actual paths
                                valid_matches = [m for m in matches if len(m) > 7 and not m.endswith('/api/"') and not m.endswith('/api/\'')]
                                
                                # Special exception for APIRouter(prefix="/api/auth") or similar where it's prefix
                                if 'prefix=' in line and 'router = APIRouter' in line:
                                    continue
                                
                                if valid_matches:
                                    found_issues.append({
                                        "file": file_path,
                                        "line": i + 1,
                                        "content": line.strip(),
                                        "matches": valid_matches
                                    })
                                    break # Avoid duplicate reporting for same line
                                    
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
                        
    return found_issues

import json

def get_expected_constants():
    json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "shared", "routes.json"))
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    expected = []
    
    def flatten(prefix, d):
        for k, v in d.items():
            snake_k = re.sub(r'(?<!^)(?=[A-Z])', '_', k).upper()
            curr_prefix = f"{prefix}_{snake_k}" if prefix else snake_k
            if isinstance(v, dict):
                flatten(curr_prefix, v)
            else:
                expected.append(curr_prefix)
                
    flatten("ADMIN_API", data.get("admin", {}).get("api", {}))
    flatten("TENANT_API", data.get("tenant", {}).get("api", {}))
    flatten("ADMIN_PAGE", data.get("admin", {}).get("pages", {}))
    flatten("TENANT_PAGE", data.get("tenant", {}).get("pages", {}))
    flatten("STATIC", data.get("static", {}))
    flatten("HEALTH", data.get("health", {}))
    
    return expected

def scan_unused_routes():
    constants = get_expected_constants()
    usage_counts = {c: 0 for c in constants}
    
    def to_camel(snake_str):
        components = snake_str.lower().split('_')
        return components[0] + ''.join(x.title() for x in components[1:])
        
    camel_map = {c: to_camel(c) for c in constants}
    
    for directory in DIRECTORIES:
        for root, dirs, files in os.walk(directory):
            if "node_modules" in dirs:
                dirs.remove("node_modules")
            for file in files:
                if any(file.endswith(ext) for ext in [".py", ".ts", ".tsx"]):
                    if file in EXCLUDE_FILES:
                        continue
                        
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            for c in constants:
                                if c in content or camel_map[c] in content:
                                    usage_counts[c] += 1
                    except Exception:
                        pass
                        
    return [c for c, count in usage_counts.items() if count == 0]

def main():
    print("Scanning codebase for hardcoded API routes...")
    issues = scan_files()
    unused = scan_unused_routes()
    
    has_errors = False
    
    if issues:
        has_errors = True
        print(f"Found {len(issues)} hardcoded API routes:")
        for issue in issues:
            rel_path = os.path.relpath(issue['file'], start=os.path.join(os.path.dirname(__file__), ".."))
            print(f"  {rel_path}:{issue['line']}")
            print(f"    Matches: {', '.join(issue['matches'])}")
            print(f"    Line: {issue['content']}")
            print()
    else:
        print("Success: No hardcoded API routes found!")
        
    if unused:
        has_errors = True
        print("\nWARNING: The following routes are defined in routes.json but are never used in the codebase:")
        for u in unused:
            print(f"  - {u}")
            
    if has_errors:
        sys.exit(1)
    else:
        print("\nAll routes are validated and used!")
        sys.exit(0)

if __name__ == "__main__":
    main()
