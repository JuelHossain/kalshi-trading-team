import { describe, expect, it } from 'vitest';
import { diffDraft } from './SettingsEditor';
import type { SettingsGroup } from './store';

const group: SettingsGroup = {
  id: 'brain',
  title: 'Brain',
  help: '',
  settings: [
    { key: 'BRAIN_MIN_EDGE', kind: 'float', label: 'Edge', help: '', restart: false, default: 0.05, value: 0.05 },
    { key: 'BRAIN_ESTIMATE_SAMPLES', kind: 'int', label: 'Samples', help: '', restart: false, default: 3, value: 3 },
    { key: 'GEMINI_API_KEY', kind: 'secret', label: 'Key', help: '', restart: true, default: '', set: true, hint: 'abcd' },
  ],
};

describe('diffDraft', () => {
  it('sends only the keys that differ from the engine', () => {
    expect(diffDraft(group, { BRAIN_MIN_EDGE: '0.05', BRAIN_ESTIMATE_SAMPLES: '5' })).toEqual({ BRAIN_ESTIMATE_SAMPLES: '5' });
  });

  it('never sends an untouched or blank secret', () => {
    expect(diffDraft(group, { GEMINI_API_KEY: '' })).toEqual({});
    expect(diffDraft(group, { GEMINI_API_KEY: '   ' })).toEqual({});
    expect(diffDraft(group, { GEMINI_API_KEY: 'new-key' })).toEqual({ GEMINI_API_KEY: 'new-key' });
  });

  it('ignores keys the group does not own', () => {
    expect(diffDraft(group, { HAND_MAX_STAKE_CENTS: 100 })).toEqual({});
  });
});
