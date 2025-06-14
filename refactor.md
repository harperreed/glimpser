# Glimpser Refactor Plan

## Executive Summary

Glimpser is a powerful real-time monitoring application that's currently functional but needs modernization. The codebase has grown organically and now requires a comprehensive refactor to improve maintainability, performance, and developer experience.

## Current State Analysis

### 🔍 What We Found
- **Monolithic Architecture**: 4,318-line `routes.py` file handling all endpoints
- **Mixed Dependency Management**: Both `requirements.txt` and `pyproject.toml` present
- **Legacy Tooling**: Using `black` instead of modern `ruff` for linting/formatting  
- **Custom CSS**: Hand-rolled styles instead of utility-first framework
- **Docker Inefficiencies**: Using `pip` instead of faster `uv` package manager
- **45 Python files** in the app directory with good test coverage (extensive test suite)

### 💪 What's Working Well
- Comprehensive feature set (RTSP streaming, AI integration, camera discovery)
- Excellent test coverage (unit, integration, and e2e tests)
- Good documentation structure
- Active development with CI/CD pipelines
- Plugin-like utilities structure already exists

## Refactor Strategy

### Phase 1: Foundation & Tooling 🔧
**Priority: HIGH**

1. **Replace Black with Ruff**
   - Update `pyproject.toml` to use ruff for linting and formatting
   - Configure ruff rules for Python 3.11+ best practices
   - Update pre-commit hooks and CI workflows
   - Run ruff format across codebase

2. **Consolidate Dependencies**  
   - Remove `requirements.txt` and `requirements-dev.txt`
   - Migrate all dependencies to `pyproject.toml`
   - Use dependency groups for dev/test/docs
   - Update Docker and documentation

3. **Modernize Docker**
   - Replace pip with uv in Dockerfile
   - Multi-stage build for smaller images
   - Update docker-compose.yaml
   - Optimize layer caching

### Phase 2: Architecture Refactor 🏗️
**Priority: HIGH**

4. **Break Up Monolithic Routes**
   - Create Flask Blueprints for logical groupings:
     - `auth` - Authentication and user management
     - `camera` - Camera discovery, configuration, streaming
     - `capture` - Screenshot and video capture endpoints  
     - `analysis` - AI/LLM processing, captions, summaries
     - `admin` - Settings, logs, system management
     - `api` - External API endpoints
   - Move route handlers to appropriate blueprint modules
   - Update imports and registrations

5. **Plugin Architecture**
   - Create `app/plugins/` directory structure
   - Define plugin interface/base classes
   - Migrate utilities to plugin pattern:
     - Camera discovery plugins (ONVIF, RTSP, etc.)
     - Alert plugins (email, SMS, webhooks)
     - AI/LLM provider plugins
     - Storage plugins
   - Implement plugin registry and loading system

### Phase 3: Code Quality & Modernization 🚀
**Priority: MEDIUM**

6. **Python Best Practices**
   - Add type hints throughout codebase
   - Use dataclasses/Pydantic models for data structures
   - Implement proper error handling patterns
   - Add proper logging throughout
   - Use context managers where appropriate
   - Implement dependency injection patterns

7. **Database & Models**
   - Review SQLAlchemy models for optimization
   - Add proper relationships and constraints
   - Implement database migrations strategy
   - Add connection pooling configuration

### Phase 4: Frontend Modernization 🎨  
**Priority: LOW**

8. **Migrate to Tailwind CSS**
   - Install and configure Tailwind CSS
   - Create design system tokens (colors, spacing, typography)
   - Migrate templates from custom CSS to Tailwind classes
   - Optimize for mobile responsiveness
   - Implement dark mode properly with Tailwind

## Implementation Timeline

### Week 1-2: Foundation
- [ ] Replace Black with Ruff
- [ ] Consolidate dependencies to pyproject.toml
- [ ] Modernize Docker setup

### Week 3-4: Architecture
- [ ] Break up routes.py into blueprints
- [ ] Create plugin architecture foundation
- [ ] Migrate 2-3 key utilities to plugins

### Week 5-6: Code Quality  
- [ ] Add type hints to core modules
- [ ] Implement better error handling
- [ ] Optimize database interactions

### Week 7-8: Frontend (Optional)
- [ ] Setup Tailwind CSS
- [ ] Migrate key templates
- [ ] Implement design system

## Success Metrics

- **Maintainability**: Reduce largest file size from 4,318 to <500 lines
- **Developer Experience**: Sub-30s test suite runtime
- **Performance**: Docker build time reduction >50%
- **Code Quality**: 100% type coverage on core modules
- **Plugin System**: 3+ utilities successfully converted to plugins

## Risk Mitigation

1. **Extensive Testing**: Leverage existing test suite throughout refactor
2. **Incremental Changes**: Each phase can be deployed independently  
3. **Feature Flags**: Use configuration to enable/disable new architecture
4. **Rollback Plan**: Maintain git branches for each phase
5. **Documentation**: Update docs alongside code changes

## Post-Refactor Benefits

- **Easier Onboarding**: Clear separation of concerns
- **Faster Development**: Plugin architecture for new features
- **Better Performance**: Optimized Docker and dependencies
- **Modern Tooling**: Ruff, uv, Tailwind for better DX
- **Scalability**: Modular architecture supports growth

---

*This refactor plan prioritizes stability and incremental improvement while modernizing the codebase for future development.*