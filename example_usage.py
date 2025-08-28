#!/usr/bin/env python3
"""
Example usage of the MCP as a Judge tools.

This demonstrates how the tools would be called by an MCP client.
Note: This is just for illustration - actual usage would be through an MCP client.
"""

# Example 1: Using judge_coding_plan
example_plan = """
I plan to create a user authentication system with the following components:

1. User model with email, password hash, and timestamps
2. JWT token generation and validation
3. Login/logout endpoints
4. Password hashing using bcrypt
5. Rate limiting for login attempts
6. Email verification for new accounts

The implementation will use:
- FastAPI for the web framework
- SQLAlchemy for database ORM
- Pydantic for data validation
- bcrypt for password hashing
- PyJWT for token handling
"""

example_design = """
SYSTEM ARCHITECTURE:
- 3-tier architecture: Presentation (FastAPI), Business Logic, Data Access (SQLAlchemy)
- RESTful API design with clear endpoint separation
- JWT-based stateless authentication
- Database schema: users table with proper indexing on email field

COMPONENTS:
1. AuthService: Handles password hashing, token generation/validation
2. UserRepository: Database operations for user management
3. RateLimiter: Redis-based rate limiting middleware
4. EmailService: Async email verification using background tasks

DATA FLOW:
1. Registration: Validate input → Hash password → Store user → Send verification email
2. Login: Validate credentials → Check rate limits → Generate JWT → Return token
3. Protected routes: Extract JWT → Validate token → Allow/deny access

SECURITY MEASURES:
- Password hashing with bcrypt (cost factor 12)
- JWT with short expiration (15 min access, 7 day refresh)
- Rate limiting: 5 attempts per minute per IP
- Input validation with Pydantic models
- HTTPS enforcement
"""

example_research = """
EXISTING SOLUTIONS ANALYZED:
1. FastAPI-Users: Full-featured but heavyweight for MVP needs
2. Flask-Login: Too basic, lacks JWT support
3. Django Auth: Overkill for microservice approach
4. Custom JWT implementation: Chosen for flexibility and learning

LIBRARIES RESEARCH:
- bcrypt vs argon2: bcrypt chosen for wider adoption and FastAPI compatibility
- PyJWT vs python-jose: PyJWT selected for simplicity and active maintenance
- Redis vs in-memory: Redis chosen for horizontal scaling capability
- SQLAlchemy vs raw SQL: ORM chosen for rapid development and type safety

BEST PRACTICES IDENTIFIED:
- OWASP authentication guidelines compliance
- JWT best practices (short expiration, secure storage)
- Rate limiting patterns for auth endpoints
- Email verification workflows
- Password policy enforcement (8+ chars, complexity)

PERFORMANCE CONSIDERATIONS:
- Database connection pooling with SQLAlchemy
- Async email sending to avoid blocking
- JWT validation caching for frequently accessed tokens
- Proper database indexing strategy
"""

example_context = """
This is for a small startup's MVP web application.
Security is important but we need to move fast.
We're using PostgreSQL as the database.
The app will initially have <1000 users.
"""

print("Example call to judge_coding_plan:")
print(f"Plan: {example_plan}")
print(f"Design: {example_design}")
print(f"Research: {example_research}")
print(f"Context: {example_context}")
print("\n" + "="*50 + "\n")

# Example 2: Using judge_code_change
example_code_change = """
@app.post("/auth/login")
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
"""

example_file_path = "app/auth/routes.py"
example_change_description = "Implement login endpoint with JWT token generation and password verification"

print("Example call to judge_code_change:")
print(f"File: {example_file_path}")
print(f"Description: {example_change_description}")
print(f"Code changes:\n{example_code_change}")
print("\n" + "="*50 + "\n")

print("Note: These tools would be called automatically by MCP clients")
print("when the mandatory descriptions trigger their usage.")
print("\n" + "="*50 + "\n")

print("Example structured responses:")
print("\nApproved response:")
print("""{
    "approved": true,
    "required_improvements": [],
    "feedback": "The coding plan follows all SWE best practices. Good use of established patterns, proper security considerations, and comprehensive testing strategy."
}""")

print("\nNeeds revision response:")
print("""{
    "approved": false,
    "required_improvements": [
        "Add input validation for email format",
        "Implement rate limiting for login attempts",
        "Add proper error logging",
        "Include integration tests for auth flow"
    ],
    "feedback": "The implementation has several security and quality issues that need to be addressed before approval."
}""")
