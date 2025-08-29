"""Tests for the prompt loader functionality."""

import pytest
from pathlib import Path

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
        template = prompt_loader.load_template("judge_coding_plan.md")
        assert template is not None
        assert hasattr(template, "render")

    def test_load_template_not_found(self) -> None:
        """Test loading a non-existent template raises error."""
        with pytest.raises(FileNotFoundError, match="Template 'nonexistent.md' not found"):
            prompt_loader.load_template("nonexistent.md")

    def test_render_judge_coding_plan(self) -> None:
        """Test rendering the judge coding plan prompt."""
        prompt = prompt_loader.render_judge_coding_plan(
            user_requirements="Build a calculator",
            plan="Create Python calculator",
            design="Use functions for operations",
            research="Researched Python math",
            context="Educational project",
            response_schema='{"type": "object"}',
        )
        
        assert "Build a calculator" in prompt
        assert "Create Python calculator" in prompt
        assert "Use functions for operations" in prompt
        assert "Researched Python math" in prompt
        assert "Educational project" in prompt
        assert '{"type": "object"}' in prompt
        assert "Software Engineering Judge" in prompt

    def test_render_judge_code_change(self) -> None:
        """Test rendering the judge code change prompt."""
        prompt = prompt_loader.render_judge_code_change(
            user_requirements="Fix the bug",
            code_change="def add(a, b): return a + b",
            file_path="calculator.py",
            change_description="Added addition function",
            response_schema='{"type": "object"}',
        )
        
        assert "Fix the bug" in prompt
        assert "def add(a, b): return a + b" in prompt
        assert "calculator.py" in prompt
        assert "Added addition function" in prompt
        assert '{"type": "object"}' in prompt
        assert "Software Engineering Judge" in prompt

    def test_render_research_validation(self) -> None:
        """Test rendering the research validation prompt."""
        prompt = prompt_loader.render_research_validation(
            user_requirements="Build a web app",
            plan="Use Flask framework",
            design="MVC architecture",
            research="Compared Flask vs Django",
        )
        
        assert "Build a web app" in prompt
        assert "Use Flask framework" in prompt
        assert "MVC architecture" in prompt
        assert "Compared Flask vs Django" in prompt
        assert "Research Quality Validation" in prompt

    def test_render_prompt_generic(self) -> None:
        """Test the generic render_prompt method."""
        prompt = prompt_loader.render_prompt(
            "judge_coding_plan.md",
            user_requirements="Test requirement",
            plan="Test plan",
            design="Test design",
            research="Test research",
            context="Test context",
            response_schema="Test schema",
        )
        
        assert "Test requirement" in prompt
        assert "Test plan" in prompt
        assert "Test design" in prompt
        assert "Test research" in prompt
        assert "Test context" in prompt
        assert "Test schema" in prompt

    def test_jinja_template_features(self) -> None:
        """Test that Jinja2 features work correctly."""
        # Test with empty context
        prompt = prompt_loader.render_judge_coding_plan(
            user_requirements="Test",
            plan="Test",
            design="Test", 
            research="Test",
            context="",  # Empty context
            response_schema="",  # Empty schema
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
        prompt = prompt_loader.render_judge_coding_plan(
            user_requirements="Global test",
            plan="Global plan",
            design="Global design",
            research="Global research",
        )
        assert "Global test" in prompt
