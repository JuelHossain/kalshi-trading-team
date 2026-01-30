# Test Generator Skill

Generate test files for new components and functions in the Sentient Alpha trading system.

## Usage

```
/test-gen <file-path>
```

## Description

Automatically generates test scaffolding based on the source file type:
- **`.tsx` files**: Creates Vitest + React Testing Library tests
- **`.ts` files**: Creates Vitest tests for utilities/hooks
- **`.py` files**: Creates pytest tests with appropriate mocks

## Examples

### Generate test for a React component
```
/test-gen frontend/src/components/Button.tsx
```
Creates: `frontend/src/components/__tests__/Button.test.tsx`

### Generate test for a Python module
```
/test-gen engine/core/vault.py
```
Creates: `engine/tests/test_vault.py`

### Generate test for a custom hook
```
/test-gen frontend/src/hooks/useAuth.ts
```
Creates: `frontend/src/hooks/__tests__/useAuth.test.ts`

## Features

- **Smart Detection**: Automatically detects React components, hooks, and Python classes/functions
- **Mock Generation**: Creates appropriate mocks for dependencies
- **Assertion Templates**: Includes common assertion patterns
- **Test Isolation**: Generates isolated tests with proper setup/cleanup
- **Coverage Ready**: Follows project testing conventions

## Test File Structure

### React Component Tests
```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ComponentName } from '../ComponentName';

describe('ComponentName', () => {
  it('renders correctly', () => {
    render(<ComponentName />);
    // assertions
  });
});
```

### Python Tests
```python
import pytest
from unittest.mock import Mock, patch
from module import function_name

class TestFunctionName:
    def test_basic_functionality(self):
        # test implementation
        pass
```

## Configuration

The skill respects existing project configurations:
- Uses `vitest.config.ts` for frontend test settings
- Uses `pytest` conventions for backend tests
- Follows existing `__tests__` directory patterns
