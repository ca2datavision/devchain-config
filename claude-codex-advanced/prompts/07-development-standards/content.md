# Prompt: How to Create Project Development Standards Documentation

Generate comprehensive yet concise developer documentation for our project. This documentation should serve as the definitive guide for developers joining or working on this project.

## Required Sections

### 1. Architecture Overview
- High-level architecture pattern (e.g., Clean Architecture, Hexagonal, Layered)
- System components and their interactions
- Technology stack and versions
- Architectural diagram or ASCII representation

### 2. Project Principles
- Core development principles (e.g., SOLID, DRY, KISS)
- Code quality standards
- Performance considerations
- Scalability guidelines

### 3. Layer Responsibilities
- Clear definition of each architectural layer
- What belongs in each layer (with examples)
- What is prohibited in each layer
- Dependencies and communication between layers

### 4. Data Contracts
- API request/response formats
- Data transfer objects (DTOs) structure
- Validation rules and constraints
- Versioning strategy for contracts
- Serialization standards

### 5. Error Handling
- Exception hierarchy and custom exceptions
- Error response format
- When to throw vs. return error results
- Error code conventions
- User-facing vs. technical error messages

### 6. Logging Standards
- Log levels and when to use each (DEBUG, INFO, WARN, ERROR)
- What to log and what to avoid logging (PII, sensitive data)
- Log format and structure
- Contextual information requirements
- Performance considerations

### 7. Configuration Management
- Configuration sources hierarchy (environment variables, files, secrets)
- Naming conventions for configuration keys
- Environment-specific configurations
- Sensitive data handling
- Required vs. optional configurations

### 8. Testing Standards
- Test pyramid (unit, integration, E2E ratios)
- Naming conventions for tests
- Test structure (Arrange-Act-Assert)
- Code coverage requirements
- Mocking and test data strategies
- CI/CD integration requirements

### 9. Security & Compliance
- Authentication and authorization patterns
- Secure coding practices
- Data protection requirements (encryption, PII handling)
- Compliance standards to follow (GDPR, HIPAA, etc.)
- Security vulnerability scanning requirements
- Dependency management and updates

### 10. Directory Layout
- Project folder structure with explanations
- File naming conventions
- Module organization rules
- Where to place new features/components

### 11. Design Principles
- Coding style guide reference
- Naming conventions (classes, methods, variables)
- Comment and documentation requirements
- Code review checklist
- Refactoring guidelines

### 12. Failure Handling & Resilience
- Retry policies and strategies
- Circuit breaker patterns
- Timeout configurations
- Graceful degradation approaches
- Health checks and monitoring

## Documentation Requirements

**Format Guidelines:**
- Use clear, concise language
- Do not include code examples, keep it clean
- Keep explanations brief but complete
- Use bullet points for clarity
- Add links to external resources where relevant

**Tone:**
- Authoritative but accessible
- Direct and actionable
- No unnecessary verbosity

**Output Format:**
- Markdown format
- Table of contents with links
- Proper heading hierarchy

## Context to Include

Customize the documentation based on:
- **Primary Language** 
- **Framework**
- **Architecture Pattern**
- **Key Technologies** [Database, message queues, caching, etc.]
- **Project Type:** [API, microservices, monolith, etc.]

Generate documentation that is strict, enforceable, and contains only valuable, actionable information.