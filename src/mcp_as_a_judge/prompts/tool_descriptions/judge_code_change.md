MANDATORY: AI programming assistant MUST call this tool after writing or editing a code file.

Args:
    code_change: The exact code that was written to a file (REQUIRED)
    user_requirements: Clear statement of what the user wants this code to achieve (REQUIRED)
    file_path: Path to the file that was created/modified
    change_description: Description of what the code accomplishes

Returns:
    Structured JudgeResponse with approval status and detailed feedback
