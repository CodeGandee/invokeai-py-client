# Roles Directory

Contains role-based system prompts, memory, and context for different AI assistant personas. Each role has its own subdirectory with specialized prompts and accumulated knowledge for that specific role or domain expertise.

## Purpose
This directory organizes role-specific context and memory for AI assistants working on the invokeai-py-client project, enabling specialized expertise for different aspects of development.

## Content Types
- Role-specific system prompts
- Accumulated knowledge and memory for each role
- Domain expertise documentation
- Role-specific workflows and processes
- Historical context for specialized roles

## Directory Structure
Each role should have its own subdirectory containing:
- `system-prompt.md` - Core role definition and behavior
- `memory.md` - Accumulated knowledge and experience
- `context.md` - Current project-specific information
- `knowledge-base.md` - Domain expertise and references

## Example Roles
- `backend-developer/` - API development and server-side logic
- `frontend-specialist/` - Client-side implementation and UI
- `devops-engineer/` - Deployment, CI/CD, and infrastructure
- `api-architect/` - API design and integration patterns
- `testing-specialist/` - Quality assurance and testing strategies

## Document Format
Each role document should include a HEADER section with:
- **Purpose**: Role responsibilities and expertise area
- **Status**: Current role activity level
- **Date**: When created or last updated
- **Dependencies**: Related roles and requirements
- **Target**: AI assistants adopting this role

## Usage
AI assistants can adopt specific roles to provide specialized expertise and maintain context across development sessions.
