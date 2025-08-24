# Project Architecture Refactoring - 2025-01-19

## Overview
Major refactoring of the ai-at-dscubed project to fix broken dependencies and modernize the codebase structure following uv workspace best practices.

## Issues Identified
- **Missing pyproject.toml files**: All workspace members (8 directories in apps/ and libs/) lacked individual package configuration files
- **Broken imports**: Code used sys.path manipulation instead of proper package imports
- **Inconsistent naming**: Directories used hyphens instead of Python-compatible underscores
- **Workspace configuration mismatch**: Root pyproject.toml expected workspace members that didn't exist as proper packages

## Actions Taken

### 1. Package Structure Creation
- Created pyproject.toml files for all 8 workspace members:
  - **Apps**: darcy, discord, discord-v2, meeting-recorder-bot, scrum-checkup
  - **Libs**: brain, custom_tools, custom_types

### 2. Directory Naming Cleanup
- Renamed directories to use Python-compatible naming:
  - `discord-v2` → `discord_v2`
  - `meeting-recorder-bot` → `meeting_recorder_bot`
  - `scrum-checkup` → `scrum_checkup`
  - `mcp-servers` → `mcp_servers`

### 3. Package Renaming & Simplification
- `libs/custom_tools` → `libs/tools`
- `libs/custom_types` → `libs/types`
- Updated all package configurations and imports accordingly

### 4. Workspace Configuration Modernization
- Fixed root pyproject.toml to properly reference workspace members
- Added `[tool.uv.sources]` sections with `{ workspace = true }` for all internal dependencies
- Removed legacy dependency references and sys.path hacks

### 5. Import Statement Cleanup
- Replaced all `from custom_tools` → `from tools`
- Removed sys.path.insert() manipulation from engine managers
- Updated MCP server integration imports
- Fixed relative imports in Discord bot modules

### 6. Package Structure Reorganization
- Moved package contents to proper nested structure matching pyproject.toml configurations
- Cleaned up directory organization for better maintainability

## Results
- ✅ `uv sync` now runs successfully without errors
- ✅ All workspace members are properly recognized and built
- ✅ Package dependencies resolve correctly with workspace references
- ✅ Eliminated all sys.path manipulation hacks
- ✅ Clean, modern uv workspace structure following best practices

## Architecture Changes
- **Before**: Monolithic structure with sys.path hacks and missing package configs
- **After**: Modern monorepo workspace with proper package isolation and dependencies

### New Structure
```
ai-at-dscubed/
├── apps/                    # Deployable applications
│   ├── darcy/              # Notion CRUD engines
│   ├── discord/            # Discord bot v1
│   ├── discord_v2/         # Discord bot v2
│   ├── meeting_recorder_bot/
│   └── scrum_checkup/
├── libs/                   # Shared libraries
│   ├── tools/              # Integrations & utilities
│   ├── types/              # Type definitions
│   └── brain/              # Data processing pipelines
└── llmgine/                # External LLM framework (workspace dep)
```

## Updated Documentation
- Simplified CLAUDE.md to focus on architectural concepts rather than implementation details
- Documented workspace dependency patterns and modern uv usage
- Removed outdated specific file paths and commands

## Package Name Collision Fix (Follow-up)

After the initial refactoring, discovered name collisions between internal packages and Python built-ins:

### Issue
- `tools` and `types` package names conflicted with Python standard library
- `uv sync` failed with workspace reference errors

### Solution
- Renamed `libs/tools` → `libs/org_tools`
- Renamed `libs/types` → `libs/org_types`  
- Updated all package names in pyproject.toml files
- Updated all import statements throughout codebase
- Updated workspace dependency references

### Files Updated
- All app pyproject.toml files (5 apps)
- Brain library pyproject.toml
- Root workspace configuration
- Import statements in engine managers and MCP servers

## Impact
This refactoring establishes a solid foundation for:
- Clean dependency management
- Easier onboarding for new developers
- Better IDE support and tooling integration
- Scalable codebase organization
- Modern Python packaging practices
- Collision-free package naming