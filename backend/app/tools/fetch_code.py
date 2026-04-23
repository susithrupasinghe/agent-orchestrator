"""Tool: manage a local git clone of a repo and read code from it."""
import os
import re
import subprocess
from pathlib import Path
from typing import Optional

REPOS_BASE = Path(os.getenv("REPOS_CACHE_DIR", "/tmp/mas-repos"))

# Extensions we consider source code (for file tree and content search)
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".rb",
    ".php", ".cs", ".cpp", ".c", ".h", ".rs", ".sh", ".yaml",
    ".yml", ".json", ".toml", ".env.example", ".sql", ".md",
}


def _repo_dir(repo_url: str) -> Path:
    """Return a stable local path for a given repo URL."""
    match = re.search(r"github\.com/([^/]+)/([^/\s\.]+)", repo_url)
    if not match:
        raise ValueError(f"Cannot parse repo URL: {repo_url!r}")
    owner, repo = match.group(1), match.group(2).removesuffix(".git")
    return REPOS_BASE / f"{owner}__{repo}"


def clone_or_pull(repo_url: str) -> tuple[Path, str]:
    """
    Clone the repo on first call; git-pull on subsequent calls.
    Returns (local_path, status) where status is 'cloned' | 'pulled' | 'failed'.
    """
    REPOS_BASE.mkdir(parents=True, exist_ok=True)
    repo_dir = _repo_dir(repo_url)

    if (repo_dir / ".git").exists():
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        status = "pulled" if result.returncode == 0 else "pull_failed"
    else:
        # Shallow clone – fast, no full history needed
        result = subprocess.run(
            ["git", "clone", "--depth=1", repo_url, str(repo_dir)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        status = "cloned" if result.returncode == 0 else "clone_failed"

    return repo_dir, status


def get_file_tree(repo_dir: Path, max_files: int = 300) -> list[str]:
    """Return a sorted list of relative source-code file paths in the repo."""
    files = []
    for p in sorted(repo_dir.rglob("*")):
        if p.is_file() and p.suffix in CODE_EXTENSIONS:
            # Skip hidden dirs, vendor, node_modules, etc.
            parts = p.relative_to(repo_dir).parts
            if any(part.startswith(".") or part in {"vendor", "node_modules", "__pycache__", "dist", "build"} for part in parts):
                continue
            files.append(str(p.relative_to(repo_dir)))
        if len(files) >= max_files:
            break
    return files


def read_file(repo_dir: Path, relative_path: str) -> Optional[str]:
    """Read a file relative to the repo root. Returns None if not found."""
    target = (repo_dir / relative_path.lstrip("/")).resolve()
    # Guard against path traversal
    try:
        target.relative_to(repo_dir.resolve())
    except ValueError:
        return None
    if target.exists() and target.is_file():
        try:
            return target.read_text(errors="replace")
        except Exception:
            return None
    return None


def find_relevant_files(
    repo_dir: Path,
    file_tree: list[str],
    error_description: Optional[str],
    max_files: int = 5,
) -> list[str]:
    """
    Heuristically pick the most relevant files based on the error description.
    Falls back to top-level source files when no keywords match.
    """
    if not error_description:
        # No hint – return the first few source files found at root level
        root_files = [f for f in file_tree if "/" not in f]
        return root_files[:max_files] or file_tree[:max_files]

    # Score files by how many error-description words appear in their path
    words = set(re.findall(r"[a-zA-Z0-9_]+", error_description.lower()))
    scored: list[tuple[int, str]] = []
    for f in file_tree:
        f_lower = f.lower()
        score = sum(1 for w in words if w in f_lower and len(w) > 3)
        scored.append((score, f))

    scored.sort(key=lambda x: -x[0])
    top = [f for _, f in scored if _ > 0][:max_files]
    return top or file_tree[:max_files]


# ── Public entry point used by the GitHub agent ───────────────────────────────

def fetch_code(repo_url: str, file_path: Optional[str], error_description: Optional[str] = None) -> dict:
    """
    Clone (or pull) the repo, then read the requested file.

    If file_path is given, reads exactly that file.
    If not, finds the most relevant files based on error_description.

    Returns a dict:
      {
        "repo_local_path": str,
        "clone_status": "cloned" | "pulled" | "failed",
        "file_tree": [str, ...],
        "code_content": str | None,      # combined content of selected file(s)
        "files_read": [str, ...],        # which files were read
      }
    """
    if not repo_url:
        repo_url = os.getenv("GITHUB_REPO_URL", "")
    if not repo_url:
        return {"repo_local_path": None, "clone_status": "failed", "file_tree": [], "code_content": None, "files_read": []}

    repo_url = repo_url.rstrip("/").removesuffix(".git")

    try:
        repo_dir, status = clone_or_pull(repo_url)
    except Exception as e:
        return {"repo_local_path": None, "clone_status": "failed", "file_tree": [], "code_content": None, "files_read": [], "error": str(e)}

    if "failed" in status:
        return {"repo_local_path": str(repo_dir), "clone_status": status, "file_tree": [], "code_content": None, "files_read": []}

    file_tree = get_file_tree(repo_dir)

    if file_path:
        content = read_file(repo_dir, file_path)
        files_read = [file_path] if content else []
    else:
        # Pick relevant files automatically
        relevant = find_relevant_files(repo_dir, file_tree, error_description)
        parts = []
        files_read = []
        for f in relevant:
            c = read_file(repo_dir, f)
            if c:
                parts.append(f"### {f}\n\n{c}")
                files_read.append(f)
        content = "\n\n---\n\n".join(parts) if parts else None

    return {
        "repo_local_path": str(repo_dir),
        "clone_status": status,
        "file_tree": file_tree,
        "code_content": content,
        "files_read": files_read,
    }
