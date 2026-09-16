from pathlib import Path


SUPPORTED_LANGUAGES = {
    "python",
    "javascript",
    "typescript",
    "java",
}


def detect_project_language(repo_path: str) -> str:
    """
    Detect the primary programming language of a repository.

    Supported:
    - Python
    - JavaScript
    - TypeScript
    - Java
    """

    root = Path(repo_path)

    # --------------------------------------------------
    # Java detection
    # --------------------------------------------------
    if (
        (root / "pom.xml").exists()
        or (root / "build.gradle").exists()
        or (root / "build.gradle.kts").exists()
        or any(root.rglob("*.java"))
    ):
        return "java"

    # --------------------------------------------------
    # TypeScript detection
    # --------------------------------------------------
    if (
        (root / "tsconfig.json").exists()
        or any(root.rglob("*.ts"))
        or any(root.rglob("*.tsx"))
    ):
        return "typescript"

    # --------------------------------------------------
    # JavaScript detection
    # --------------------------------------------------
    if (
        (root / "package.json").exists()
        or any(root.rglob("*.js"))
        or any(root.rglob("*.jsx"))
    ):
        return "javascript"

    # --------------------------------------------------
    # Python detection
    # --------------------------------------------------
    if (
        (root / "requirements.txt").exists()
        or (root / "pyproject.toml").exists()
        or (root / "setup.py").exists()
        or any(root.rglob("*.py"))
    ):
        return "python"

    return "unknown"


def get_language_details(language: str) -> dict:
    """
    Return execution information for the detected language.
    """

    details = {
        "python": {
            "language": "Python",
            "extensions": [".py"],
            "command": "python",
            "check": "python -m compileall .",
        },

        "javascript": {
            "language": "JavaScript",
            "extensions": [".js", ".jsx"],
            "command": "node",
            "check": "npm run build",
        },

        "typescript": {
            "language": "TypeScript",
            "extensions": [".ts", ".tsx"],
            "command": "npm",
            "check": "npm run build",
        },

        "java": {
            "language": "Java",
            "extensions": [".java"],
            "command": "javac",
            "check": "javac",
        },
    }

    return details.get(
        language,
        {
            "language": "Unknown",
            "extensions": [],
            "command": None,
            "check": None,
        },
    )