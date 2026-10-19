"""Check repository text hygiene and inline relative Markdown file links."""

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit


root = Path(__file__).resolve().parent.parent
files = subprocess.check_output(
    ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
    cwd=root,
).decode().split("\0")
errors = []
documents = 0
links = 0

for name in sorted(set(files) - {""}):
    path = root / name
    if not path.is_file() or (path.suffix not in {".md", ".yml", ".yaml", ".py"} and name != "LICENSE"):
        continue
    source = path.read_text(encoding="utf-8")
    if not source.endswith("\n"):
        errors.append(f"{name}: missing final newline")
    for number, line in enumerate(source.splitlines(), 1):
        if line.rstrip() != line:
            errors.append(f"{name}:{number}: trailing whitespace")
        if re.match(r"^(<{7}|={7}|>{7})(?: |$)", line):
            errors.append(f"{name}:{number}: possible merge conflict marker")
    if path.suffix != ".md":
        continue
    documents += 1
    # Check inline file links, not examples in fenced code blocks.
    prose = re.sub(r"^```[^\n]*\n.*?^```[^\n]*$", "", source, flags=re.M | re.S)
    for target in re.findall(r"\]\(([^\s)]+)\)", prose):
        url = urlsplit(target)
        if url.scheme or url.netloc or not url.path:
            continue
        links += 1
        destination = (path.parent / unquote(url.path)).resolve()
        if not destination.is_relative_to(root) or not destination.exists():
            errors.append(f"{name}: invalid relative link: {target}")

if errors:
    raise SystemExit("\n".join(errors))
print(f"PASS: text hygiene; {documents} Markdown files; {links} relative file links")
