"""
Plan formatting utilities for presenting implementation plans to users.

This module provides utilities to format implementation plans in a way that's
suitable for display in IDEs like Cursor and Copilot, with clear markdown
formatting and user-friendly presentation.
"""

from typing import Any


class PlanFormatter:
    """Formats implementation plans for user presentation."""

    @staticmethod
    def format_plan_for_approval(
        plan: str,
        design: str,
        research: str,
        technical_decisions: list[dict[str, str]],
        implementation_scope: dict[str, Any],
        language_specific_practices: list[str],
        user_questions: list[str],
    ) -> tuple[str, str]:
        """
        Format a plan for user approval with IDE-friendly markdown.
        
        Args:
            plan: Raw implementation plan
            design: Design details
            research: Research findings
            technical_decisions: List of technical decisions made
            implementation_scope: Scope information (files, complexity)
            language_specific_practices: Best practices to follow
            user_questions: Questions for user consideration
            
        Returns:
            Tuple of (formatted_plan, plan_summary)
        """
        # Create executive summary
        plan_summary = PlanFormatter._create_executive_summary(
            plan, technical_decisions, implementation_scope
        )
        
        # Format the detailed plan
        formatted_plan = PlanFormatter._format_detailed_plan(
            plan, design, research, technical_decisions, 
            implementation_scope, language_specific_practices, user_questions
        )
        
        return formatted_plan, plan_summary

    @staticmethod
    def _create_executive_summary(
        plan: str, 
        technical_decisions: list[dict[str, str]], 
        implementation_scope: dict[str, Any]
    ) -> str:
        """Create a concise executive summary of the plan."""
        # Extract key points from plan (first few sentences)
        plan_lines = plan.split('\n')
        key_points = []
        
        for line in plan_lines[:5]:  # First 5 lines
            line = line.strip()
            if line and not line.startswith('#') and len(line) > 20:
                key_points.append(line)
                if len(key_points) >= 2:  # Limit to 2 key points
                    break
        
        summary_parts = []
        
        if key_points:
            summary_parts.append("**Overview:** " + " ".join(key_points))
        
        # Add key technical decisions
        if technical_decisions:
            key_tech = technical_decisions[:3]  # Top 3 decisions
            tech_summary = ", ".join([f"{d.get('decision', 'Unknown')}: {d.get('choice', 'Unknown')}" for d in key_tech])
            summary_parts.append(f"**Key Technologies:** {tech_summary}")
        
        # Add scope summary
        files_to_create = implementation_scope.get('files_to_create', [])
        files_to_modify = implementation_scope.get('files_to_modify', [])
        total_files = len(files_to_create) + len(files_to_modify)
        complexity = implementation_scope.get('estimated_complexity', 'Unknown')
        
        summary_parts.append(f"**Scope:** {total_files} files, {complexity} complexity")
        
        return "\n\n".join(summary_parts)

    @staticmethod
    def _format_detailed_plan(
        plan: str,
        design: str,
        research: str,
        technical_decisions: list[dict[str, str]],
        implementation_scope: dict[str, Any],
        language_specific_practices: list[str],
        user_questions: list[str],
    ) -> str:
        """Format the detailed implementation plan with proper markdown."""
        sections = []
        
        # Add plan content with proper formatting
        if plan:
            sections.append("## 📋 Implementation Plan\n")
            sections.append(PlanFormatter._format_markdown_content(plan))
        
        # Add design section
        if design:
            sections.append("\n## 🎨 Design Architecture\n")
            sections.append(PlanFormatter._format_markdown_content(design))
        
        # Add research section if significant
        if research and len(research.strip()) > 100:
            sections.append("\n## 🔍 Research & Analysis\n")
            sections.append(PlanFormatter._format_markdown_content(research))
        
        # Add technical decisions
        if technical_decisions:
            sections.append("\n## ⚙️ Technical Decisions\n")
            for decision in technical_decisions:
                decision_name = decision.get('decision', 'Unknown Decision')
                choice = decision.get('choice', 'Unknown Choice')
                rationale = decision.get('rationale', 'No rationale provided')
                
                sections.append(f"### {decision_name}\n")
                sections.append(f"**Selected:** {choice}\n")
                sections.append(f"**Rationale:** {rationale}\n")
        
        # Add implementation scope
        sections.append("\n## 📁 Implementation Scope\n")
        
        files_to_create = implementation_scope.get('files_to_create', [])
        files_to_modify = implementation_scope.get('files_to_modify', [])
        complexity = implementation_scope.get('estimated_complexity', 'Unknown')
        
        if files_to_create:
            sections.append("**Files to Create:**\n")
            for file in files_to_create:
                sections.append(f"- `{file}`\n")
        
        if files_to_modify:
            sections.append("\n**Files to Modify:**\n")
            for file in files_to_modify:
                sections.append(f"- `{file}`\n")
        
        sections.append(f"\n**Estimated Complexity:** {complexity}\n")
        
        # Add best practices
        if language_specific_practices:
            sections.append("\n## ✅ Best Practices & Standards\n")
            sections.append("The implementation will follow these practices:\n\n")
            for practice in language_specific_practices:
                sections.append(f"- {practice}\n")
        
        # Add user questions
        if user_questions:
            sections.append("\n## ❓ Questions for Your Consideration\n")
            for i, question in enumerate(user_questions, 1):
                sections.append(f"{i}. {question}\n")
        
        return "".join(sections)

    @staticmethod
    def _format_markdown_content(content: str) -> str:
        """Ensure content is properly formatted as markdown."""
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append("")
                continue
                
            # Ensure proper heading formatting
            if line.startswith('#'):
                formatted_lines.append(line)
            # Add proper list formatting
            elif line.startswith('-') or line.startswith('*'):
                if not line.startswith('- ') and not line.startswith('* '):
                    line = '- ' + line[1:].strip()
                formatted_lines.append(line)
            # Add numbered list formatting
            elif line[0].isdigit() and '.' in line[:5]:
                formatted_lines.append(line)
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines) + '\n'

    @staticmethod
    def generate_user_questions(
        technical_decisions: list[dict[str, str]],
        implementation_scope: dict[str, Any],
        plan_content: str,
    ) -> list[str]:
        """Generate relevant questions for user consideration."""
        questions = []
        
        # Questions about technical decisions
        if technical_decisions:
            questions.append("Do the technical choices align with your project goals and constraints?")
            
            # Specific questions based on decisions
            for decision in technical_decisions:
                decision_type = decision.get('decision', '').lower()
                choice = decision.get('choice', '')
                
                if 'database' in decision_type:
                    questions.append(f"Are you comfortable with {choice} for data storage and scalability needs?")
                elif 'framework' in decision_type or 'library' in decision_type:
                    questions.append(f"Does {choice} fit your team's expertise and project timeline?")
                elif 'api' in decision_type:
                    questions.append(f"Will {choice} meet your integration and client requirements?")
        
        # Questions about scope
        complexity = implementation_scope.get('estimated_complexity', '').lower()
        if 'high' in complexity or 'complex' in complexity:
            questions.append("Given the complexity, would you prefer to break this into smaller phases?")
        
        total_files = len(implementation_scope.get('files_to_create', [])) + len(implementation_scope.get('files_to_modify', []))
        if total_files > 10:
            questions.append("This involves many files - are there any specific areas you'd like to prioritize?")
        
        # Questions about implementation approach
        if 'test' in plan_content.lower():
            questions.append("What level of test coverage do you expect for this implementation?")
        
        if 'deploy' in plan_content.lower() or 'production' in plan_content.lower():
            questions.append("Do you have specific deployment or production environment requirements?")
        
        # Always ask about timeline and priorities
        questions.append("Are there any specific deadlines or priorities that should influence the implementation order?")
        questions.append("Would you like any additional features or considerations included in this plan?")
        
        return questions[:6]  # Limit to 6 questions to avoid overwhelming the user
