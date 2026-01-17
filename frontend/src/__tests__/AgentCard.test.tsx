import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import AgentCard from '@/components/AgentCard';
import { AgentStatus } from '@shared/types';

describe('AgentCard Component', () => {
    const mockAgent = {
        id: 1,
        name: 'Test Agent',
        role: 'Tester',
        description: 'Testing the component',
        status: AgentStatus.WORKING,
        lastAction: 'Waiting',
        model: 'Vitest 1.0',
    };

    it('renders agent name and role', () => {
        render(<AgentCard agent={mockAgent} />);

        expect(screen.getByText('Test Agent')).toBeInTheDocument();
        expect(screen.getByText('Tester')).toBeInTheDocument();
    });

    it('displays the correct model', () => {
        render(<AgentCard agent={mockAgent} />);
        expect(screen.getByText('Vitest 1.0')).toBeInTheDocument();
    });

    it('shows executing status when active', () => {
        render(<AgentCard agent={mockAgent} isActive={true} />);
        expect(screen.getByText('EXECUTING DIRECTIVE...')).toBeInTheDocument();
    });
});
