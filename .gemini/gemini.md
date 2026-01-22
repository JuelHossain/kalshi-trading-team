# Project-Specific Rules
## Testing Requirements
- Always run backend tests (`npm run test:backend`) after modifying TypeScript code
- Always run frontend tests (`npm run test:frontend`) after modifying React components
- Test Python engine modules individually before integration
- Never skip testing when modifying agent logic or API integrations
## Deployment Protocol
- Build both backend and frontend before deploying: `npm run build`
- Deploy using PM2: `npm start` (uses ecosystem.config.cjs)
- Verify all 3 processes are running: backend, frontend, and Python engine
- Check PM2 logs after deployment: `npm run logs`
## Git Commit Standards
- Commit after every significant feature completion
- Use conventional commits: `feat:`, `fix:`, `refactor:`, `test:`
- Always pull before push to avoid conflicts
- Include affected components in commit message (e.g., "feat(engine): add analyst agent")
## Python Engine Development
- Always activate virtual environment before working: `source engine/venv/bin/activate`
- Update requirements.txt when adding dependencies
- Use structured JSON logging for all agent outputs
- Maintain agent independence - each agent should be testable in isolation
## API Key Management
- Never commit [.env](cci:7://file:///home/jrrahman01/workspace/active/kalshi-trading-team/engine/.env:0:0-0:0) or [.env.local](cci:7://file:///home/jrrahman01/workspace/active/kalshi-trading-team/.env.local:0:0-0:0) files
- Verify all required API keys before testing: GEMINI_API_KEY, KALSHI_API_KEY, RAPID_API_KEY
- Use paper trading mode by default (IS_PAPER_TRADING=true)
## Code Quality
- TypeScript: Maintain strict type safety, no `any` types
- Python: Follow PEP 8, use type hints
- React: Use TypeScript for all components, proper prop typing
- Shared types: Update `shared/types.ts` when modifying data structures