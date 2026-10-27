import { readFileSync, existsSync } from 'node:fs';

if (process.env.VITE_PUBLIC_EXHIBIT !== 'true') {
  console.log('[REQUIEM] Building the local API edition.');
  process.exit(0);
}

const file = new URL('../public/exhibit.json', import.meta.url);
if (!existsSync(file)) throw new Error('Public build blocked: export frontend/public/exhibit.json first.');
const data = JSON.parse(readFileSync(file, 'utf8'));
if (data.kind !== 'real_git_history' || data.publicMode !== true ||
    !/^https:\/\/github\.com\/[\w.-]+\/[\w.-]+$/.test(data.repoUrl || '')) {
  throw new Error('Public build blocked: snapshot must come from real GitHub history.');
}
const stones = data.stones || [];
if (!stones.length || data.audit?.selected_cases !== stones.length ||
    data.audit?.verified_cases !== stones.length) {
  throw new Error('Public build blocked: every case must have passed the Git-object audit.');
}
const reports = data.precomputedNarrations || {};
for (const stone of stones) {
  const report = reports[String(stone.id)];
  if (!report?.ai_interpretation?.epitaph || !report?.factual_view?.claims?.length) {
    throw new Error(`Public build blocked: missing locally generated, separated narration for case ${stone.id}`);
  }
}
if (data.evaluation?.reportable_as_complete !== true ||
    data.evaluation?.completed < 1) {
  throw new Error('Public build blocked: reviewed benchmark evidence is missing or incomplete.');
}
console.log(`[REQUIEM] Public snapshot verified: ${stones.length} audited cases, ${data.evaluation.completed} human-reviewed explanations.`);
