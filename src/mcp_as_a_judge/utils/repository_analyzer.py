"""
Repository analysis utilities for detecting programming languages, frameworks, and patterns.

This module provides utilities to analyze repository structure and content to inform
requirement gathering and technology decisions in a language-agnostic way.
"""

import json
import os
from collections import Counter
from pathlib import Path
from typing import ClassVar


class RepositoryAnalyzer:
    """Analyzes repository structure to detect languages, frameworks, and patterns."""

    # Common dependency/config files that indicate languages
    LANGUAGE_INDICATORS: ClassVar = {
        "python": {
            "files": [
                "requirements.txt",
                "pyproject.toml",
                "setup.py",
                "setup.cfg",
                "Pipfile",
                "poetry.lock",
            ],
            "extensions": [".py"],
            "directories": ["__pycache__", ".venv", "venv", "env"],
        },
        "javascript": {
            "files": [
                "package.json",
                "package-lock.json",
                "yarn.lock",
                "pnpm-lock.yaml",
            ],
            "extensions": [".js", ".jsx", ".ts", ".tsx"],
            "directories": ["node_modules", "dist", "build"],
        },
        "go": {
            "files": ["go.mod", "go.sum", "Gopkg.toml", "Gopkg.lock"],
            "extensions": [".go"],
            "directories": ["vendor"],
        },
        "rust": {
            "files": ["Cargo.toml", "Cargo.lock"],
            "extensions": [".rs"],
            "directories": ["target"],
        },
        "java": {
            "files": [
                "pom.xml",
                "build.gradle",
                "build.gradle.kts",
                "gradle.properties",
            ],
            "extensions": [".java", ".kt", ".scala"],
            "directories": ["target", "build", ".gradle"],
        },
        "csharp": {
            "files": ["*.csproj", "*.sln", "packages.config", "project.json"],
            "extensions": [".cs", ".vb", ".fs"],
            "directories": ["bin", "obj", "packages"],
        },
        "php": {
            "files": ["composer.json", "composer.lock"],
            "extensions": [".php"],
            "directories": ["vendor"],
        },
        "ruby": {
            "files": ["Gemfile", "Gemfile.lock", "*.gemspec"],
            "extensions": [".rb"],
            "directories": ["vendor/bundle"],
        },
    }

    # Framework-specific indicators
    FRAMEWORK_INDICATORS: ClassVar = {
        "django": ["manage.py", "settings.py", "wsgi.py"],
        "flask": ["app.py", "application.py", "run.py"],
        "fastapi": ["main.py", "app.py"],
        "react": ["src/App.js", "src/App.jsx", "src/App.tsx", "public/index.html"],
        "vue": ["vue.config.js", "src/main.js", "src/App.vue"],
        "angular": ["angular.json", "src/main.ts", "src/app/app.module.ts"],
        "express": ["server.js", "app.js", "index.js"],
        "spring": ["src/main/java", "application.properties", "application.yml"],
        "laravel": ["artisan", "composer.json", "app/Http/Kernel.php"],
        "rails": [
            "Gemfile",
            "config/application.rb",
            "app/controllers/application_controller.rb",
        ],
    }

    def __init__(self, repo_path: str = "."):
        """Initialize analyzer with repository path."""
        self.repo_path = Path(repo_path).resolve()

    def analyze(self) -> dict:
        """
        Perform comprehensive repository analysis.

        Returns:
            Dictionary containing analysis results
        """
        if not self.repo_path.exists():
            return {"error": f"Repository path does not exist: {self.repo_path}"}

        analysis = {
            "repository_path": str(self.repo_path),
            "languages": self._detect_languages(),
            "frameworks": self._detect_frameworks(),
            "project_structure": self._analyze_structure(),
            "dependency_info": self._analyze_dependencies(),
            "recommendations": self._generate_recommendations(),
        }

        return analysis

    def _detect_languages(self) -> dict:
        """Detect programming languages used in the repository."""
        language_scores = {}
        file_counts = Counter()

        # Walk through repository
        for root, dirs, files in os.walk(self.repo_path):
            # Skip common ignore directories
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d not in ["node_modules", "__pycache__", "target", "build", "dist"]
            ]

            for file in files:
                file_path = Path(root) / file
                extension = file_path.suffix.lower()

                # Count file extensions
                if extension:
                    file_counts[extension] += 1

                # Check against language indicators
                for lang, indicators in self.LANGUAGE_INDICATORS.items():
                    score = 0

                    # Check for specific files
                    if file in indicators["files"]:
                        score += 10

                    # Check for file extensions
                    if extension in indicators["extensions"]:
                        score += 1

                    if score > 0:
                        language_scores[lang] = language_scores.get(lang, 0) + score

        # Determine primary language
        primary_language = (
            max(language_scores.items(), key=lambda x: x[1])[0]
            if language_scores
            else None
        )

        return {
            "detected": language_scores,
            "primary": primary_language,
            "file_extensions": dict(file_counts.most_common(10)),
            "confidence": "high"
            if language_scores and max(language_scores.values()) >= 10
            else "medium"
            if language_scores
            else "low",
        }

    def _detect_frameworks(self) -> dict:
        """Detect frameworks and libraries used."""
        framework_scores = {}

        for _root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d not in ["node_modules", "__pycache__", "target", "build", "dist"]
            ]

            for framework, indicators in self.FRAMEWORK_INDICATORS.items():
                score = 0
                for indicator in indicators:
                    if indicator in files:
                        score += 5
                    # Check for partial matches in directory structure
                    for file in files:
                        if indicator in file:
                            score += 1

                if score > 0:
                    framework_scores[framework] = (
                        framework_scores.get(framework, 0) + score
                    )

        return {
            "detected": framework_scores,
            "likely": [fw for fw, score in framework_scores.items() if score >= 5],
            "possible": [
                fw for fw, score in framework_scores.items() if 1 <= score < 5
            ],
        }

    def _analyze_structure(self) -> dict:
        """Analyze project structure and organization patterns."""
        structure = {"directories": [], "key_files": [], "patterns": []}

        # Get top-level directories and files
        if self.repo_path.exists():
            for item in self.repo_path.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    structure["directories"].append(item.name)
                elif item.is_file():
                    structure["key_files"].append(item.name)

        # Identify common patterns
        dirs = set(structure["directories"])
        files = set(structure["key_files"])

        if "src" in dirs:
            structure["patterns"].append("source_directory_pattern")
        if "tests" in dirs or "test" in dirs:
            structure["patterns"].append("dedicated_test_directory")
        if "docs" in dirs or "documentation" in dirs:
            structure["patterns"].append("documentation_directory")
        if "README.md" in files or "README.rst" in files:
            structure["patterns"].append("readme_documentation")
        if ".gitignore" in files:
            structure["patterns"].append("version_control")

        return structure

    def _analyze_dependencies(self) -> dict:
        """Analyze dependency management and key dependencies."""
        dependencies = {}

        # Check for common dependency files
        dependency_files = {
            "package.json": self._parse_package_json,
            "requirements.txt": self._parse_requirements_txt,
            "Cargo.toml": self._parse_cargo_toml,
            "go.mod": self._parse_go_mod,
            "pom.xml": self._parse_pom_xml,
        }

        for filename, parser in dependency_files.items():
            file_path = self.repo_path / filename
            if file_path.exists():
                try:
                    dependencies[filename] = parser(file_path)
                except Exception as e:
                    dependencies[filename] = {"error": str(e)}

        return dependencies

    def _parse_package_json(self, file_path: Path) -> dict:
        """Parse package.json for JavaScript/Node.js dependencies."""
        try:
            with open(file_path) as f:
                data = json.load(f)

            return {
                "name": data.get("name", "unknown"),
                "version": data.get("version", "unknown"),
                "dependencies": list(data.get("dependencies", {}).keys()),
                "dev_dependencies": list(data.get("devDependencies", {}).keys()),
                "scripts": list(data.get("scripts", {}).keys()),
            }
        except Exception as e:
            return {"error": str(e)}

    def _parse_requirements_txt(self, file_path: Path) -> dict:
        """Parse requirements.txt for Python dependencies."""
        try:
            with open(file_path) as f:
                lines = f.readlines()

            dependencies = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Extract package name (before version specifiers)
                    pkg_name = (
                        line.split("==")[0]
                        .split(">=")[0]
                        .split("<=")[0]
                        .split(">")[0]
                        .split("<")[0]
                        .split("~=")[0]
                    )
                    dependencies.append(pkg_name.strip())

            return {"dependencies": dependencies}
        except Exception as e:
            return {"error": str(e)}

    def _parse_cargo_toml(self, file_path: Path) -> dict:
        """Parse Cargo.toml for Rust dependencies."""
        try:
            # Simple TOML parsing for dependencies section
            with open(file_path) as f:
                content = f.read()

            dependencies = []
            in_deps_section = False
            for line in content.split("\n"):
                line = line.strip()
                if line == "[dependencies]":
                    in_deps_section = True
                elif line.startswith("[") and line != "[dependencies]":
                    in_deps_section = False
                elif in_deps_section and "=" in line:
                    dep_name = line.split("=")[0].strip()
                    dependencies.append(dep_name)

            return {"dependencies": dependencies}
        except Exception as e:
            return {"error": str(e)}

    def _parse_go_mod(self, file_path: Path) -> dict:
        """Parse go.mod for Go dependencies."""
        try:
            with open(file_path) as f:
                content = f.read()

            dependencies = []
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("require "):
                    dep = line.replace("require ", "").split(" ")[0]
                    dependencies.append(dep)
                elif (
                    line
                    and not line.startswith("module")
                    and not line.startswith("go ")
                    and " " in line
                ):
                    # Handle multi-line require blocks
                    dep = line.split(" ")[0]
                    if dep and not dep.startswith("//"):
                        dependencies.append(dep)

            return {"dependencies": dependencies}
        except Exception as e:
            return {"error": str(e)}

    def _parse_pom_xml(self, file_path: Path) -> dict:
        """Parse pom.xml for Java/Maven dependencies."""
        try:
            # Simple XML parsing for Maven dependencies
            with open(file_path) as f:
                content = f.read()

            # This is a very basic parser - in production, use proper XML parsing
            dependencies = []
            if "<dependencies>" in content:
                deps_section = content.split("<dependencies>")[1].split(
                    "</dependencies>"
                )[0]
                # Extract artifactId values (simplified)
                import re

                artifact_ids = re.findall(
                    r"<artifactId>(.*?)</artifactId>", deps_section
                )
                dependencies = artifact_ids

            return {"dependencies": dependencies}
        except Exception as e:
            return {"error": str(e)}

    def _generate_recommendations(self) -> dict:
        """Generate recommendations based on analysis."""
        languages = self._detect_languages()
        frameworks = self._detect_frameworks()

        recommendations = {
            "technology_stack": "unclear",
            "suggested_approach": "ask_user",
            "reasoning": [],
        }

        if languages["confidence"] == "high" and languages["primary"]:
            recommendations["technology_stack"] = "detected"
            recommendations["suggested_approach"] = "confirm_or_choose_different"
            recommendations["reasoning"].append(
                f"Clear {languages['primary']} project detected - recommend continuing with {languages['primary']} for consistency"
            )
            recommendations["reasoning"].append(
                "However, user may choose different language for valid reasons (microservices, tooling, team expertise, etc.)"
            )

            if frameworks["likely"]:
                recommendations["reasoning"].append(
                    f"Likely frameworks: {', '.join(frameworks['likely'])}"
                )
        elif languages["confidence"] == "medium":
            recommendations["technology_stack"] = "mixed_or_unclear"
            recommendations["suggested_approach"] = "clarify_with_user"
            recommendations["reasoning"].append(
                "Multiple languages detected or unclear primary language"
            )
        else:
            recommendations["technology_stack"] = "empty_or_new"
            recommendations["suggested_approach"] = "ask_user_preferences"
            recommendations["reasoning"].append("No clear technology stack detected")

        return recommendations

    def get_summary_text(self) -> str:
        """Get a human-readable summary of the repository analysis."""
        analysis = self.analyze()

        if "error" in analysis:
            return f"Error analyzing repository: {analysis['error']}"

        summary_parts = []

        # Language summary
        languages = analysis["languages"]
        if languages["primary"]:
            summary_parts.append(
                f"**Primary Language**: {languages['primary'].title()}"
            )
            if languages["confidence"] == "high":
                summary_parts.append("(High confidence)")
            else:
                summary_parts.append("(Medium confidence)")
        else:
            summary_parts.append("**Primary Language**: Not clearly detected")

        # Framework summary
        frameworks = analysis["frameworks"]
        if frameworks["likely"]:
            summary_parts.append(
                f"**Likely Frameworks**: {', '.join(frameworks['likely'])}"
            )
        elif frameworks["possible"]:
            summary_parts.append(
                f"**Possible Frameworks**: {', '.join(frameworks['possible'])}"
            )

        # Structure summary
        structure = analysis["project_structure"]
        if structure["patterns"]:
            summary_parts.append(
                f"**Project Patterns**: {', '.join(structure['patterns'])}"
            )

        # Recommendations
        recommendations = analysis["recommendations"]
        if recommendations["suggested_approach"] == "confirm_or_choose_different":
            summary_parts.append(
                f"**Recommendation**: Continue with {languages['primary']} for consistency, but user choice is respected"
            )
            summary_parts.append(
                "**Note**: User may choose different language for valid architectural reasons"
            )
        else:
            summary_parts.append(
                f"**Recommendation**: {recommendations['suggested_approach']}"
            )

        if recommendations["reasoning"]:
            summary_parts.append(
                f"**Analysis**: {'; '.join(recommendations['reasoning'])}"
            )

        return "\n".join(summary_parts)
