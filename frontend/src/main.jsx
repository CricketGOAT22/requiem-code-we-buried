import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const short = (value) => value ? value.slice(0, 8) : '—';
const isSurvivor = (stone) => stone?.possibleSuccessors?.length > 0;

function Mark({ size = 24 }) {
  return <svg width={size} height={size} viewBox="0 0 38 38" fill="none" aria-hidden="true">
    <path d="M19 3C11.5 3 6 8.6 6 16v18h26V16C32 8.6 26.5 3 19 3Z" stroke="currentColor" strokeWidth="1.7"/>
    <path d="M19 11v15m-6-9h12" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/>
    <path d="M2 34h34" stroke="currentColor" strokeWidth="1.7"/>
  </svg>;
}

function Moon() {
  return <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M20.5 14.2A8.8 8.8 0 0 1 9.8 3.5 8.8 8.8 0 1 0 20.5 14.2Z" stroke="currentColor" strokeWidth="1.5"/></svg>;
}

function Arrow({ diagonal = false }) {
  return <span aria-hidden="true">{diagonal ? '↗' : '→'}</span>;
}

function FooterStars() {
  return <div className="stars" aria-hidden="true">{Array.from({ length: 18 }, (_, i) => <i key={i} style={{ '--x': `${(i * 37 + 11) % 97}%`, '--y': `${(i * 31 + 8) % 84}%`, '--delay': `${(i % 7) * 0.33}s` }} />)}</div>;
}

async function request(url, options) {
  const response = await fetch(url, options);
  let payload;
  try { payload = await response.json(); } catch { throw new Error('Local server returned an unreadable response.'); }
  if (!response.ok) throw new Error(payload.error || `Request failed (HTTP ${response.status}).`);
  return payload;
}

function Epitaph({ stone, active, onClick, number }) {
  const survivor = isSurvivor(stone);
  return <button type="button" className={`grave ${active ? 'grave-active' : ''}`} onClick={onClick} aria-pressed={active} aria-label={`Open case file for ${stone.name}: ${survivor ? 'possible successor' : 'no successor detected'}`}>
    <div className={`grave-halo ${survivor ? 'halo-life' : 'halo-lost'}`} />
    <div className="grave-stone">
      <div className="grave-rune">✦</div>
      <div className="grave-rip">R · I · P</div>
      <div className="grave-fn">{stone.name}<span>()</span></div>
      <div className="grave-line" />
      <div className="grave-date">{short(stone.oldCommit)} → {short(stone.newCommit)}</div>
    </div>
    <div className="grave-ground" />
    <div className="grave-label"><span className={survivor ? 'dot dot-violet' : 'dot dot-gold'} />{survivor ? 'A TRACE REMAINS' : 'NO TRACE FOUND'}</div>
    <div className="grave-index">0{number + 1}</div>
  </button>;
}

function CodeBlock({ label, code, sub, empty = false }) {
  return <div className="code-pane">
    <div className="code-head"><div><span className={`code-status ${empty ? 'empty' : ''}`} />{label}</div><small>{sub}</small></div>
    <div className="code-lines">{empty ? <div className="void-code"><span>∅</span><p>No structural successor detected in this revision.</p></div> :
      <pre><code>{(code || '').trim().split('\n').map((line, index) => <span className="code-line" key={index}><span className="line-num">{String(index + 1).padStart(2, '0')}</span><span>{line}</span></span>)}</code></pre>}
    </div>
  </div>;
}

function EvidenceCard({ entry, active, toggle }) {
  return <div className={`evidence-card ${active ? 'evidence-expanded' : ''}`}>
    <button type="button" onClick={toggle} aria-expanded={active}>
      <span className="evidence-id">{entry.id}</span>
      <span className="evidence-claim">{entry.claim}</span>
      <span className="evidence-arrow">{active ? '−' : '+'}</span>
    </button>
    {active && <div className="evidence-detail">{entry.source_excerpt ? <pre>{entry.source_excerpt}</pre> : <p>This observation comes from comparing the two verified Git revisions.</p>}</div>}
  </div>;
}

function AiPanel({ stone, ai, onSummon, loading, error, publicMode }) {
  return <div className="ai-panel" id="seance">
    <div className="ai-decor" aria-hidden="true">✧</div>
    <div className="section-eyebrow"><Moon /> THE SÉANCE CHAMBER <span className="horizontal-rule" /></div>
    <div className="ai-layout">
      <div>
        <h2>Let the code <em>speak.</em></h2>
        <p className="muted">Gemma reads the Git evidence and writes a creative epitaph. The factual record is built separately by Python; the model cannot edit it.</p>
        {publicMode ? <>
          <a className="primary-btn" href="#protocol"><span>EXPLORE THE METHOD</span><span className="arrow-circle">↗</span></a>
          <p className="public-note">Public exhibition: Gemma generated this epitaph locally before publication. New generations require the local edition and Ollama.</p>
        </> : <button type="button" className="primary-btn" onClick={onSummon} disabled={loading}>
          <span>{loading ? 'SUMMONING GEMMA…' : ai ? 'SUMMON AGAIN' : 'SUMMON THE MEMORY'}</span>
          <span className={loading ? 'spinner' : 'arrow-circle'}>{loading ? '' : '↗'}</span>
        </button>}
        <div className="model-caption"><span className="dot dot-violet"/> {ai?.model?.toUpperCase() || 'GEMMA 3 4B'} <span className="caption-divider">/</span> {publicMode ? 'PRECOMPUTED ON A LOCAL MAC' : 'LOCAL OLLAMA'} <span className="caption-divider">/</span> NO CLOUD INFERENCE</div>
        {error && <div className="error-callout" role="alert">{error}</div>}
      </div>
      <div className="ai-answer" aria-live="polite">
        {loading ? <div className="answer-loading"><div className="circle-orbit">✳</div><p>Searching the silence between commits…</p><small>Local inference may take a few seconds.</small></div> :
          ai ? <>
            <span className="answer-kicker">AI-GENERATED EPITAPH</span>
            <blockquote>“{ai.ai_interpretation.epitaph}”</blockquote>
            {ai.factual_view ? <section className="claim-gate" aria-label="Factual Git record">
              <span className="answer-kicker safe-kicker">◆ THE EVIDENCE FIREWALL · FACTS FROM GIT</span>
              <ul>{ai.factual_view.claims.map(item => <li key={item.id}><span>{item.id}</span>{item.text}</li>)}</ul>
              <small>Constructed from the scan report, not generated by Gemma. An independent audit against Git objects is required to verify the report. The digest is not a proof of authenticity.</small>
            </section> : <p className="error-callout">This older response has no bounded factual view. Re-summon Gemma after restarting the updated backend.</p>}
            <details className="unverified-drawer">
              <summary>READ THE RAW AI INTERPRETATION — UNVERIFIED</summary>
              <p>{ai.ai_interpretation.explanation}</p>
              <small>Research artifact only. A valid citation ID does not prove the claim it accompanies.</small>
            </details>
            <div className="answer-metrics">{publicMode && <span>PRECOMPUTED LOCAL OUTPUT · NOT LIVE AI</span>}<span>MODEL: {ai.model}</span><span>INFERENCE: {ai.metrics?.total_seconds ?? '?'}s</span><span>CITED IDS: {ai.ai_interpretation.evidence_ids.join(', ')}</span>{ai.factual_view && <span>REPORT DIGEST: {ai.factual_view.sha256.slice(0, 12)}</span>}</div>
          </> : <div className="answer-empty"><div className="large-ghost" aria-hidden="true">◌</div><span>THE SPIRITS ARE QUIET</span><p>Choose to summon a story. Verified evidence remains visible whether the model runs or not.</p></div>}
      </div>
    </div>
    <p className="ai-warning">The firewall prevents model-generated explanations from appearing as verified historical facts. It does not automatically establish report authenticity or prevent inaccurate claims in the creative epitaph.</p>
  </div>;
}

function CaseFile({ stone, number, ai, narrate, loading, error, realMode, publicMode }) {
  const [opened, setOpened] = useState(['E1']);
  useEffect(() => { setOpened(['E1']); }, [stone?.id]);
  if (!stone) return null;
  const successor = stone.possibleSuccessors[0];
  const survived = Boolean(successor);
  return <section className="case-section" id="case-file" aria-label="Function case file">
    <div className="section-eyebrow"><span>02</span> CASE FILE <span className="horizontal-rule"/><span>CLASSIFIED: EVIDENCE FIRST</span></div>
    <div className="case-heading"><div>
      <span className="small-label">CASE NO. {String(number + 1).padStart(3, '0')} — SELECTED FUNCTION</span>
      <h2>{stone.name}<span>()</span></h2>
      <p>{stone.path} · line {stone.line} · {realMode ? 'two verified revisions from a public project' : 'two real Git commits in our synthetic demo'}</p>
    </div><span className={`case-status ${survived ? 'alive' : 'lost'}`}>{survived ? '◈ POSSIBLE AFTERLIFE' : '◌ NO MATCH DETECTED'}</span></div>
    {stone.caseGroup?.related_removals > 1 && <div className="related-case-note">
      <strong>◈ RELATED METHODS GROUPED</strong>
      <span>{stone.caseGroup.label}. This gravestone represents {stone.caseGroup.related_removals} method-level observations ({stone.caseGroup.method_names.join(', ')}), not independent proof of {stone.caseGroup.related_removals} separate migrations.</span>
    </div>}
    <div className="case-timeline">
      <div className="timeline-node"><span className="timeline-symbol">✦</span><div><small>LAST VERIFIED APPEARANCE</small><strong>{short(stone.oldCommit)}</strong><span>{stone.path}</span></div></div>
      <div className="timeline-road"><span>GIT HISTORY</span><Arrow /></div>
      <div className="timeline-node"><span className="timeline-symbol death">✕</span><div><small>FIRST VERIFIED ABSENCE</small><strong>{short(stone.newCommit)}</strong><span>{stone.path}</span>{stone.newCommitUrl && <a href={stone.newCommitUrl} rel="noreferrer" target="_blank" className="commit-link">VIEW ORIGINAL COMMIT ↗</a>}</div></div>
    </div>
    <div className="code-grid">
      <CodeBlock label="THE DECEASED" code={stone.source} sub={stone.path} />
      <CodeBlock label="THE POSSIBLE SUCCESSOR" code={successor?.source} sub={successor ? `${successor.path} · ${Math.round(successor.similarity * 100)}% structure` : 'Nothing found'} empty={!successor}/>
    </div>
    {stone.contextWarnings?.length > 0 && <div className="context-trap">
      <div className="context-trap-symbol">!</div>
      <div className="context-trap-body">
        <span className="context-kicker">{realMode ? 'VERIFIED CONTEXT DIFFERENCE' : 'THE FALSE RESURRECTION / VERIFIED CONTEXT CHANGE'}</span>
        <strong>{realMode ? 'Structural similarity hides context differences.' : '100% structural similarity. A different result.'}</strong>
        <p>{stone.contextWarnings[0].message}</p>
        <div className="context-comparison"><span>BEFORE <b>{stone.contextWarnings[0].variable} = {stone.contextWarnings[0].before}</b></span><span>AFTER <b>{stone.contextWarnings[0].variable} = {stone.contextWarnings[0].after}</b></span></div>
        <small>{realMode ? 'A context difference does not by itself prove a particular runtime outcome; check behavior separately.' : 'For this controlled fixture, an input of age 20 passes the original threshold and fails the new one. This is a constructed counterexample, not a claim about a public repository.'}</small>
      </div>
    </div>}
    <div className="interpret-strip"><div className="strip-icon">✳</div><div><strong>{survived ? 'A resemblance, not a resurrection.' : 'Absence is not proof of extinction.'}</strong><p>{stone.interpretation}</p></div><div className="strip-metric">{survived ? `${Math.round(successor.similarity * 100)}%` : '—'}<small>STRUCTURAL SCORE</small></div></div>
    <div className="evidence-section"><div className="section-eyebrow"><span>03</span> EVIDENCE LEDGER <span className="horizontal-rule"/><span>{stone.observations.length} OBSERVATIONS</span></div><p className="muted">Open a claim to inspect the original source excerpt. These entries come from deterministic Git analysis, not the language model.</p>
      <div className="evidence-stack">{stone.observations.map((entry) => <EvidenceCard key={entry.id} entry={entry} active={opened.includes(entry.id)} toggle={() => setOpened(curr => curr.includes(entry.id) ? curr.filter(e => e !== entry.id) : [...curr, entry.id])}/>)}</div>
    </div>
    <AiPanel stone={stone} ai={ai} onSummon={narrate} loading={loading} error={error} publicMode={publicMode}/>
  </section>;
}

function EvidenceStudy({ evaluation }) {
  if (!evaluation) return null;
  return <section className="evidence-study" id="study" aria-label="Gemma evidence reliability experiment">
    <div className="section-eyebrow"><span>04</span> THE EVIDENCE LAB <span className="horizontal-rule"/> SMALL HUMAN-REVIEWED STUDY</div>
    <div className="study-grid">
      <div>
        <h2>The citations were real.<br/><em>The conclusions weren't always justified.</em></h2>
        <p>We compared two prompting strategies on the same real Git cases. A reviewer judged each AI explanation against the evidence—not whether its citation IDs merely existed.</p>
        <p className="study-caveat">This was a small, curated, single-reviewer study with {evaluation.total_valid_outputs} outputs, not a general model factuality score. The review conditions were hidden in the review interface but not cryptographically blinded.</p>
      </div>
      <div className="study-results">
        {evaluation.groups?.map(group => <div className="study-result" key={`${group.model}-${group.method}`}>
          <span>{group.model} / {group.method === 'guarded' ? 'EVIDENCE-CAUTIOUS' : 'BASELINE'}</span>
          <strong>{group.supported}<small> / {group.reviewed} fully supported</small></strong>
          <p>{group.unsupported} unsupported · {group.unclear} uncertain</p>
        </div>)}
        <p className="study-result-footer">Results are from the preserved local evaluation workbook; the page does not regrade its own model output.</p>
      </div>
    </div>
  </section>;
}

function App() {
  const [exhibit, setExhibit] = useState(null);
  const [failure, setFailure] = useState('');
  const [activeId, setActiveId] = useState(0);
  const [narrations, setNarrations] = useState({});
  const [loading, setLoading] = useState(false);
  const [aiError, setAiError] = useState('');
  const publicMode = import.meta.env.VITE_PUBLIC_EXHIBIT === 'true';
  useEffect(() => {
    request(publicMode ? '/exhibit.json' : '/api/exhibit')
      .then(data => {
        if (publicMode && (!data.publicMode || !data.audit || !data.stones?.length ||
            !data.precomputedNarrations ||
            Object.keys(data.precomputedNarrations).length !== data.stones.length)) {
          throw new Error('Public exhibit has not been exported with an audited Git report and local Gemma narration.');
        }
        setExhibit(data);
      })
      .catch(err => setFailure(err.message));
  }, [publicMode]);
  const selected = exhibit?.stones.find(stone => stone.id === activeId);
  const selectStone = (id) => {
    setActiveId(id);
    setAiError('');
    document.getElementById('case-file')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
  const summon = async () => {
    if (!selected || loading || publicMode) return;
    const target = activeId;
    setLoading(true);
    setAiError('');
    try {
      const report = await request('/api/narrate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: target }) });
      setNarrations(previous => ({ ...previous, [target]: report }));
    } catch (err) { setAiError(err.message); }
    finally { setLoading(false); }
  };
  const saveEvidence = () => {
    if (!exhibit) return;
    const json = JSON.stringify({ ...exhibit, localAiReports: publicMode ? {} : narrations }, null, 2);
    const url = URL.createObjectURL(new Blob([json], { type: 'application/json' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = 'requiem-evidence.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  return <div className="app-shell">
    <div className="ambient-lights" aria-hidden="true"/><FooterStars/>
    <header className="topbar"><a href="#top" className="brand"><Mark/><span>REQUIEM</span><i>.</i></a><nav aria-label="Main navigation"><a href="#cemetery">THE CEMETERY</a><a href="#case-file">CASE FILE</a><a href="#protocol">THE PROTOCOL</a></nav><span className="nav-status"><span className="dot dot-green"/> {publicMode ? 'PUBLIC · PRECOMPUTED' : 'LOCAL-FIRST EXHIBIT'}</span></header>
    <main id="top">
      <section className="hero"><div className="hero-side left" aria-hidden="true">EST. MMXXVI / THE ARCHIVE OF THE FORGOTTEN</div><div className="hero-content"><div className="eyebrow"><span className="eyebrow-star">✳</span> AN EXHIBITION OF THE FORGOTTEN <span className="eyebrow-star">✳</span></div><div className="hero-title"><div>THE CODE</div><div>WE <em>BURIED</em><span className="period">.</span></div></div><p className="hero-copy">Every deleted function leaves a trace. Follow the commits. Find what survived. Let the machine remember what the codebase forgot.</p><a className="hero-link" href="#cemetery">ENTER THE CEMETERY <span>↓</span></a></div><div className="hero-side right" aria-hidden="true">NO FALSE MEMORIES / ONLY VERIFIED TRACES</div><div className="hero-moon" aria-hidden="true"/><div className="hero-land" aria-hidden="true"/><div className="hero-dusk" aria-hidden="true"/></section>
      <section className="exhibit" id="cemetery"><div className="exhibit-heading"><div className="section-eyebrow"><span>01</span> THE DIGITAL CEMETERY <span className="horizontal-rule"/> {exhibit?.kind === 'real_git_history' ? 'REAL HISTORY · VERIFIED CODE' : 'TWO COMMITS. FIVE STORIES.'}</div><h2>Not every ending <em>is an ending.</em></h2><p>Select a gravestone to examine the exact code and Git observations that remain.</p></div>
        {failure ? <div className="connection-error" role="alert"><h3>The local archive is sleeping.</h3><p>Could not load the exhibition: {failure}</p><p>{publicMode ? 'Export frontend/public/exhibit.json on your Mac before building the public site.' : <>Start <code>python3 -m scripts.serve</code> from the project root, then reload this page.</>}</p></div> : !exhibit ? <div className="connection-loading">Opening the sealed archive…</div> : <>
        <div className="stats"><div><span>REPOSITORY</span><strong>{exhibit.repoName}</strong></div><div><span>{exhibit.kind === 'real_git_history' ? 'CASES SHOWN' : 'FUNCTIONS MISSING'}</span><strong>{String(exhibit.summary.removed).padStart(2, '0')}</strong></div><div><span>POSSIBLE AFTERLIVES</span><strong>{String(exhibit.summary.possibleSurvivors).padStart(2, '0')}</strong></div><div><span>UNMATCHED</span><strong>{String(exhibit.summary.unmatched).padStart(2, '0')}</strong></div></div>
        {publicMode && <p className="public-audit"><strong>◆ VERIFIED AGAINST GIT OBJECTS:</strong> {exhibit.audit?.verified_cases}/{exhibit.audit?.selected_cases} curated cases passed a fresh source audit before export. Gemma passages were generated on a local machine and are not verified claims.</p>}
        {exhibit.kind === 'real_git_history' && exhibit.scan && <p className="scan-coverage">Audited window: {exhibit.scan.commits_visited} commits · {exhibit.scan.candidate_removals_found} candidate removals observed · {exhibit.scan.curation?.related_method_observations_grouped ?? 0} related method observations grouped · {exhibit.stones.length} curated cases on display. Counts describe the scanned window, not the complete repository.</p>}
        <div className="graveyard"><div className="graveyard-fog" aria-hidden="true"/>{exhibit.stones.map((stone, i) => <Epitaph key={stone.id} stone={stone} active={stone.id === activeId} onClick={() => selectStone(stone.id)} number={i}/>)}</div>
        {exhibit.kind === 'synthetic_git_fixture' ?
          <div className="paradox-banner"><div><span className="paradox-kicker">THE EXPERIMENT THAT CHANGES EVERYTHING</span><h3>Same function structure.<br/><em>Different behavior.</em></h3><p>One specially constructed case has a perfect structural match—yet a module-level constant changes from 18 to 21. A matching fingerprint cannot guarantee equivalent behavior.</p></div><button type="button" onClick={() => selectStone(exhibit.stones.find(s => s.name === 'can_enter')?.id ?? 0)}>INVESTIGATE THE PARADOX <Arrow diagonal/></button><div className="paradox-orbit" aria-hidden="true">1.00 <small>≠</small></div></div>
          : <div className="paradox-banner"><div><span className="paradox-kicker">REAL CODE. DOCUMENTED REVISIONS.</span><h3>A trace is not <em>a verdict.</em></h3><p>These removals come from a public repository's local Git checkout, not a constructed story. Inspect the code and original commits before deciding whether a function truly survived.</p></div><button type="button" onClick={() => selectStone(exhibit.stones.find(s => s.possibleSuccessors.length)?.id ?? 0)}>EXAMINE A CASE <Arrow diagonal/></button><div className="paradox-orbit" aria-hidden="true">GIT</div></div> }
        <div className="fixture-note"><span>✦</span><p><strong>{exhibit.kind === 'real_git_history' ? 'REAL REPOSITORY · LOCAL CODE ANALYSIS' : 'LIVE GIT EVIDENCE · SYNTHETIC STORY'}</strong> — {exhibit.disclaimer} {exhibit.repoUrl && <a className="repo-link" href={exhibit.repoUrl} target="_blank" rel="noreferrer">VIEW REPOSITORY ↗</a>}</p><button type="button" onClick={saveEvidence}>EXPORT EVIDENCE <Arrow diagonal/></button></div>
        <CaseFile stone={selected} number={exhibit.stones.findIndex(item => item.id === activeId)} ai={publicMode ? exhibit.precomputedNarrations?.[String(activeId)] : narrations[activeId]} narrate={summon} loading={loading} error={aiError} realMode={exhibit.kind === 'real_git_history'} publicMode={publicMode}/>
        </>}
      </section>
      <EvidenceStudy evaluation={exhibit?.evaluation}/>
      <section className="protocol" id="protocol"><div><div className="section-eyebrow"><span>04</span> THE REQUIEM PROTOCOL</div><h2>Trust the evidence.<br/><em>Question the ghost.</em></h2></div><div className="protocol-right"><p><strong>01 / DETECT</strong><br/>Python's AST and Git identify function definitions that disappear between commits.</p><p><strong>02 / INVESTIGATE</strong><br/>Structural fingerprints search newly appearing functions for possible successors—never proof of equivalence.</p><p><strong>03 / SEPARATE</strong><br/>Python compiles bounded Git observations. Gemma creates the epitaph; its free-form interpretation remains unverified behind a disclosure.</p><p><strong>04 / AUDIT</strong><br/>Recheck exported observations against original Git objects. A valid citation ID is not proof that an AI claim follows from it.</p></div></section>
    </main>
    <footer><div className="footer-mark"><Mark size={28}/><span>REQUIEM<span className="accent">.</span></span></div><p>Not every ghost is a hallucination. Some are in the Git history.</p><span>BUILT WITH OPEN-WEIGHT AI · 2026</span></footer>
  </div>;
}

createRoot(document.getElementById('root')).render(<App />);
