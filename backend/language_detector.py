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

    Also detects nested frontend projects such as:

        repository/
            backend/
            frontend/
                package.json
                tsconfig.json
    """

    root = Path(repo_path)

    # =========================================================
    # JAVA
    # =========================================================

    if (
        (root / "pom.xml").exists()
        or (root / "build.gradle").exists()
        or (root / "build.gradle.kts").exists()
        or any(
            p.is_file()
            for p in root.rglob("*.java")
            if "node_modules" not in p.parts
        )
    ):
        return "java"

    # =========================================================
    # TYPEScript - ROOT PROJECT
    # =========================================================

    if (
        (root / "tsconfig.json").exists()
        or (root / "package.json").exists()
        and any(
            p.is_file()
            for p in root.rglob("*.ts")
            if "node_modules" not in p.parts
        )
        or any(
            p.is_file()
            for p in root.rglob("*.tsx")
            if "node_modules" not in p.parts
        )
    ):
        return "typescript"

    # =========================================================
    # NESTED NODE / NEXT.JS PROJECT
    #
    # Example:
    #
    # repository/
    #     frontend/
    #         package.json
    #         next.config.ts
    #         tsconfig.json
    # =========================================================

    for package_file in root.rglob("package.json"):

        if "node_modules" in package_file.parts:
            continue

        package_root = package_file.parent

        if (
            (package_root / "tsconfig.json").exists()
            or any(
                p.is_file()
                for p in package_root.rglob("*.ts")
                if "node_modules" not in p.parts
            )
            or any(
                p.is_file()
                for p in package_root.rglob("*.tsx")
                if "node_modules" not in p.parts
            )
        ):
            return "typescript"

    # =========================================================
    # JAVASCRIPT
    # =========================================================

    if (
        (root / "package.json").exists()
        or any(
            p.is_file()
            for p in root.rglob("*.js")
            if "node_modules" not in p.parts
        )
        or any(
            p.is_file()
            for p in root.rglob("*.jsx")
            if "node_modules" not in p.parts
        )
    ):
        return "javascript"

    # =========================================================
    # PYTHON
    # =========================================================

    if (
        (root / "requirements.txt").exists()
        or (root / "pyproject.toml").exists()
        or (root / "setup.py").exists()
        or any(
            p.is_file()
            for p in root.rglob("*.py")
            if (
                "node_modules" not in p.parts
                and ".venv" not in p.parts
                and "venv" not in p.parts
            )
        )
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
            "command": "npm",
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