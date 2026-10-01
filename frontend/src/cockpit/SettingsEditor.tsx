/**
 * The settings editor: every group the engine's registry describes, each
 * setting as the right control for its kind, saved per group. The engine
 * validates, persists to its .env, applies live where it can, and says
 * which keys need a restart. Secrets are write-only: the engine only ever
 * tells us whether one is set and its last four characters.
 */
import { useMemo, useState, type CSSProperties } from 'react';
import { AC, ACI, ACS, E, F, G, glassStyle, mix, PALETTES, R, RL, SG, SGS, T1, T3, T4 } from './palette';
import { useCockpit, type SettingSpec, type SettingsGroup, type UpdateReport } from './store';

export type Draft = Record<string, unknown>;

/** Only keys whose draft differs from the engine's value are sent. */
export function diffDraft(group: SettingsGroup, draft: Draft): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const s of group.settings) {
    if (!(s.key in draft)) continue;
    const v = draft[s.key];
    if (s.kind === 'secret' || s.kind === 'multiline_secret') {
      if (typeof v === 'string' && v.trim() !== '') out[s.key] = v;
      continue;
    }
    if (String(v) !== String(s.value)) out[s.key] = v;
  }
  return out;
}

export function SettingsEditor({
  onSave,
  onRestart,
}: {
  onSave: (changes: Record<string, unknown>) => Promise<UpdateReport>;
  onRestart: () => Promise<void>;
}) {
  const s = useCockpit();
  const pal = PALETTES[s.palette];
  const glassCard: CSSProperties = { borderRadius: RL, padding: 20, ...glassStyle(pal) };

  if (!s.settingsGroups.length) {
    return (
      <div style={{ ...glassCard, fontSize: 12, color: T4 }}>
        {s.connected ? 'Reading the engine settings…' : 'Engine unreachable; settings appear when it answers.'}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {s.restartPending.length > 0 && (
        <div style={{ ...glassCard, borderColor: mix(ACS, 60, E), display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontFamily: 'var(--font-heading)', fontSize: 17, color: T1 }}>Restart to apply</div>
            <div style={{ fontSize: 12, color: T3, marginTop: 4 }}>
              Saved, but the engine only reads these at start-up: {s.restartPending.join(', ')}.
            </div>
          </div>
          <button
            onClick={() => void onRestart()}
            style={{ flex: 'none', border: `1px solid ${ACS}`, background: ACS, color: ACI, borderRadius: 999, padding: '10px 22px', fontWeight: 600, fontSize: 14, cursor: 'pointer' }}
          >
            Restart engine
          </button>
        </div>
      )}
      {s.settingsGroups.map((group) => (
        <GroupCard key={group.id} group={group} onSave={onSave} />
      ))}
      {s.envFile && (
        <div style={{ fontSize: 11, color: F, padding: '0 4px' }}>
          Saved values are written to <span className="num">{s.envFile}</span> on the engine's machine, so they survive a restart.
        </div>
      )}
    </div>
  );
}

function GroupCard({ group, onSave }: { group: SettingsGroup; onSave: (changes: Record<string, unknown>) => Promise<UpdateReport> }) {
  const pal = PALETTES[useCockpit((s) => s.palette)];
  const [draft, setDraft] = useState<Draft>({});
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<UpdateReport | null>(null);
  const changes = useMemo(() => diffDraft(group, draft), [group, draft]);
  const dirty = Object.keys(changes).length > 0;

  const save = async () => {
    if (!dirty || busy) return;
    setBusy(true);
    const r = await onSave(changes);
    setReport(r);
    setBusy(false);
    if (!Object.keys(r.errors).length) setDraft({});
  };

  return (
    <div style={{ borderRadius: RL, padding: 20, ...glassStyle(pal) }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontFamily: 'var(--font-heading)', fontSize: 19, color: T1 }}>{group.title}</div>
          <div style={{ fontSize: 12, color: T3, marginTop: 4 }}>{group.help}</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {dirty && (
            <button
              onClick={() => {
                setDraft({});
                setReport(null);
              }}
              style={{ border: `1px solid ${E}`, background: 'transparent', color: T4, borderRadius: 999, padding: '7px 14px', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
            >
              Discard
            </button>
          )}
          <button
            onClick={() => void save()}
            disabled={!dirty || busy}
            style={{ border: `1px solid ${dirty ? ACS : E}`, background: dirty ? ACS : 'transparent', color: dirty ? ACI : T4, borderRadius: 999, padding: '7px 16px', fontSize: 12, fontWeight: 600, cursor: dirty ? 'pointer' : 'default', opacity: busy ? 0.6 : 1 }}
          >
            {busy ? 'Saving…' : dirty ? `Save ${Object.keys(changes).length}` : 'Saved'}
          </button>
        </div>
      </div>

      {report && (
        <div
          role="status"
          style={{
            marginTop: 12,
            fontSize: 12,
            padding: '9px 13px',
            borderRadius: R,
            background: Object.keys(report.errors).length ? mix(ACS, 10, G) : mix(SGS, 10, G),
            color: Object.keys(report.errors).length ? AC : SG,
          }}
        >
          {report.applied.length > 0 && <div>Applied now: {report.applied.join(', ')}.</div>}
          {report.restart_required.length > 0 && <div>Saved; restart to apply: {report.restart_required.join(', ')}.</div>}
          {Object.entries(report.errors).map(([k, v]) => (
            <div key={k}>{k === '_' ? v : `${k}: ${v}`}</div>
          ))}
        </div>
      )}

      <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', marginTop: 14 }}>
        {group.settings.map((spec) => (
          <SettingRow
            key={spec.key}
            spec={spec}
            draft={draft[spec.key]}
            error={report?.errors[spec.key]}
            onChange={(v) => setDraft((d) => ({ ...d, [spec.key]: v }))}
          />
        ))}
      </div>
    </div>
  );
}

function SettingRow({ spec, draft, error, onChange }: { spec: SettingSpec; draft: unknown; error?: string; onChange: (v: unknown) => void }) {
  const pal = PALETTES[useCockpit((s) => s.palette)];
  const isSecret = spec.kind === 'secret' || spec.kind === 'multiline_secret';
  const current = draft !== undefined ? draft : spec.value;
  const changed = draft !== undefined && String(draft) !== String(spec.value) && !(isSecret && draft === '');
  const field: CSSProperties = {
    width: '100%',
    padding: '9px 13px',
    borderRadius: spec.kind === 'multiline_secret' ? R : 999,
    ...glassStyle(pal),
    border: `1px solid ${error ? ACS : changed ? mix(SGS, 60, E) : E}`,
    color: T1,
    fontSize: 13,
    outline: 'none',
  };

  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 0 }}>
      <span style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 8 }}>
        <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: T4 }}>{spec.label}</span>
        <span style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: spec.restart ? AC : F }}>
          {spec.restart ? 'restart' : 'live'}
        </span>
      </span>

      {spec.kind === 'bool' ? (
        <button
          type="button"
          role="switch"
          aria-checked={!!current}
          onClick={() => onChange(!current)}
          style={{ alignSelf: 'flex-start', position: 'relative', width: 52, height: 30, borderRadius: 999, border: `1px solid ${current ? ACS : E}`, background: current ? ACS : mix(G, 60), cursor: 'pointer', padding: 0, transition: 'background 0.2s' }}
        >
          <span style={{ position: 'absolute', top: 3, left: current ? 25 : 3, width: 22, height: 22, borderRadius: 999, background: current ? ACI : T4, transition: 'left 0.2s' }} />
        </button>
      ) : spec.kind === 'choice' ? (
        <select value={String(current ?? '')} onChange={(e) => onChange(e.target.value)} style={field}>
          {(spec.choices ?? []).map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      ) : spec.kind === 'multiline_secret' ? (
        <textarea
          value={typeof draft === 'string' ? draft : ''}
          onChange={(e) => onChange(e.target.value)}
          placeholder={spec.set ? `set · ends ${spec.hint || '····'} · paste to replace` : 'not set · paste the PEM key'}
          rows={4}
          spellCheck={false}
          style={{ ...field, fontFamily: 'var(--font-mono, monospace)', fontSize: 11, resize: 'vertical' }}
        />
      ) : spec.kind === 'secret' ? (
        <input
          type="password"
          value={typeof draft === 'string' ? draft : ''}
          onChange={(e) => onChange(e.target.value)}
          placeholder={spec.set ? `set · ends ${spec.hint || '····'} · type to replace` : 'not set'}
          autoComplete="new-password"
          style={field}
        />
      ) : (
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input
            type={spec.kind === 'int' || spec.kind === 'float' ? 'number' : 'text'}
            value={String(current ?? '')}
            onChange={(e) => onChange(e.target.value)}
            min={spec.minimum}
            max={spec.maximum}
            step={spec.step ?? (spec.kind === 'int' ? 1 : 'any')}
            className="num"
            style={field}
          />
          {spec.unit && <span style={{ fontSize: 11, color: F, flex: 'none' }}>{spec.unit}</span>}
        </span>
      )}

      <span style={{ fontSize: 11, color: error ? AC : T3, lineHeight: 1.5 }}>
        {error || spec.help}
        {!isSecret && spec.kind !== 'bool' && spec.default !== '' && spec.default !== undefined && (
          <span style={{ color: F }}> Default {String(spec.default)}.</span>
        )}
      </span>
    </label>
  );
}
