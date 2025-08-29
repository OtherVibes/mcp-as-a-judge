"""Tests for the prompt loader functionality."""

from pathlib import Path

import pytest

from mcp_as_a_judge.prompt_loader import PromptLoader, prompt_loader


class TestPromptLoader:
    """Test the PromptLoader class."""

    def test_prompt_loader_initialization(self) -> None:
        """Test that prompt loader initializes correctly."""
        loader = PromptLoader()
        assert loader.prompts_dir.exists()
        assert loader.prompts_dir.name == "prompts"

    def test_custom_prompts_dir(self) -> None:
        """Test initialization with custom prompts directory."""
        custom_dir = Path(__file__).parent / "fixtures"
        loader = PromptLoader(custom_dir)
        assert loader.prompts_dir == custom_dir

    def test_load_template_success(self) -> None:
        """Test loading an existing template."""
        template = prompt_loader.load_template("user/judge_coding_plan.md")
        assert template is not None
        assert hasattr(template, "render")

    def test_load_template_not_found(self) -> None:
        """Test loading a non-existent template raises error."""
        with pytest.raises(
            FileNotFoundError, match="Template 'nonexistent.md' not found"
        ):
            prompt_loader.load_template("nonexistent.md")

    def test_render_judge_coding_plan_user(self) -> None:
        """Test rendering the judge coding plan user prompt."""
        prompt = prompt_loader.render_prompt(
            "user/judge_coding_plan.md",
            user_requirements="Build a calculator",
            plan="Create Python calculator",
            design="Use functions for operations",
            research="Researched Python math",
            context="Educational project",
        )

        assert "Build a calculator" in prompt
        assert "Create Python calculator" in prompt
        assert "Use functions for operations" in prompt
        assert "Researched Python math" in prompt
        assert "Educational project" in prompt
        assert "Please evaluate the following coding plan" in prompt

    def test_render_judge_coding_plan_system(self) -> None:
        """Test rendering the judge coding plan system prompt."""
        prompt = prompt_loader.render_prompt(
            "system/judge_coding_plan.md",
            response_schema='{"type": "object"}',
        )

        assert '{"type": "object"}' in prompt
        assert "Software Engineering Judge" in prompt
        assert "expert software engineering judge" in prompt

    def test_render_judge_code_change_user(self) -> None:
        """Test rendering the judge code change user prompt."""
        prompt = prompt_loader.render_prompt(
            "user/judge_code_change.md",
            user_requirements="Fix the bug",
            code_change="def add(a, b): return a + b",
            file_path="calculator.py",
            change_description="Added addition function",
        )

        assert "Fix the bug" in prompt
        assert "def add(a, b): return a + b" in prompt
        assert "calculator.py" in prompt
        assert "Added addition function" in prompt
        assert "Please review the following code" in prompt

    def test_render_research_validation_user(self) -> None:
        """Test rendering the research validation user prompt."""
        prompt = prompt_loader.render_prompt(
            "user/research_validation.md",
            user_requirements="Build a web app",
            plan="Use Flask framework",
            design="MVC architecture",
            research="Compared Flask vs Django",
        )

        assert "Build a web app" in prompt
        assert "Use Flask framework" in prompt
        assert "MVC architecture" in prompt
        assert "Compared Flask vs Django" in prompt
        assert "Please validate the research quality" in prompt

    def test_render_prompt_generic(self) -> None:
        """Test the generic render_prompt method."""
        prompt = prompt_loader.render_prompt(
            "user/judge_coding_plan.md",
            user_requirements="Test requirement",
            plan="Test plan",
            design="Test design",
            research="Test research",
            context="Test context",
        )

        assert "Test requirement" in prompt
        assert "Test plan" in prompt
        assert "Test design" in prompt
        assert "Test research" in prompt
        assert "Test context" in prompt

    def test_jinja_template_features(self) -> None:
        """Test that Jinja2 features work correctly."""
        # Test with empty context
        prompt = prompt_loader.render_prompt(
            "user/judge_coding_plan.md",
            user_requirements="Test",
            plan="Test",
            design="Test",
            research="Test",
            context="",  # Empty context
        )

        # Should not have broken formatting and should contain all test values
        assert "## Context" in prompt
        assert "## Plan" in prompt
        assert prompt.count("Test") >= 4  # Should appear at least 4 times (our inputs)

    def test_global_prompt_loader_instance(self) -> None:
        """Test that the global prompt_loader instance works."""
        assert prompt_loader is not None
        assert isinstance(prompt_loader, PromptLoader)

        # Should be able to render prompts
        prompt = prompt_loader.render_prompt(
            "user/judge_coding_plan.md",
            user_requirements="Global test",
            plan="Global plan",
            design="Global design",
            research="Global research",
        )
        assert "Global test" in prompt
