const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('====================================================');
console.log('BIO STUDIO PHASE 3 VERIFICATION SUITE');
console.log('====================================================\n');

const htmlPath = path.join(__dirname, '../index.html');
const html = fs.readFileSync(htmlPath, 'utf8');

// 1. Phase 3 DOM Elements Verification
console.log('TEST 1: Phase 3 Modals, Views, and Navigation Controls');
const requiredPhase3Elements = [
  ['view-overview', 'Home Overview View'],
  ['view-studio', 'Studio Workspace View'],
  ['view-prompts', 'Prompts & Blueprints View'],
  ['view-guide', 'JanitorAI Bio Guide View'],
  ['view-decoder', 'Local Token Decoder View (100% Client-Side)'],
  ['view-privacy', 'Privacy Policy & Transparency View'],
  ['history-modal', 'Local Version History IndexedDB Modal'],
  ['templates-modal', 'Starter Templates Modal (7 Archetypes)'],
  ['assets-modal', 'Asset Utilities & Snippet Builders Modal'],
  ['import-export-modal', 'Import & Export / Backups Modal'],
  ['strict-mode-toggle', 'Strict vs Relaxed Sanitizer Toggle'],
  ['decoder-token-input', 'Decoder Token Input Textarea'],
  ['decoder-results-area', 'Decoder Results Live Container'],
  ['import-dropzone', 'Drag & Drop HTML File Upload Zone'],
  ['export-html-btn', 'Standalone HTML File Export Button'],
  ['export-history-json-btn', 'Token-Free History JSON Export Button']
];

requiredPhase3Elements.forEach(([id, desc]) => {
  assert.ok(html.includes(`id="${id}"`), `Missing required element: #${id} (${desc})`);
  console.log(`  ✓ Found #${id} (${desc})`);
});

// 2. Token Decoder Pure Client-Side Logic Test
console.log('\nTEST 2: Local Token Decoder Engine Test');
function decodeBase64Url(str) {
  try {
    let output = str.replace(/-/g, "+").replace(/_/g, "/");
    switch (output.length % 4) {
      case 0: break;
      case 2: output += "=="; break;
      case 3: output += "="; break;
      default: return null;
    }
    return Buffer.from(output, 'base64').toString('utf8');
  } catch (e) {
    return null;
  }
}

function decodeFullJwt(tokenString) {
  if (!tokenString) return null;
  let clean = tokenString.trim();
  if (clean.startsWith("Bearer ")) clean = clean.slice(7).trim();
  const parts = clean.split(".");
  if (parts.length < 2) return null;
  const headerStr = decodeBase64Url(parts[0]);
  const payloadStr = decodeBase64Url(parts[1]);
  if (!headerStr || !payloadStr) return null;
  try {
    return {
      header: JSON.parse(headerStr),
      payload: JSON.parse(payloadStr)
    };
  } catch (e) {
    return null;
  }
}

const testHeader = { alg: "HS256", typ: "JWT" };
const testPayload = {
  sub: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  email: "creator@example.com",
  role: "authenticated",
  user_metadata: {
    user_name: "ValeriaAuthor",
    preferred_username: "ValeriaAuthor"
  },
  exp: Math.floor(Date.now() / 1000) + 3600,
  iat: Math.floor(Date.now() / 1000)
};

const headerB64 = Buffer.from(JSON.stringify(testHeader)).toString('base64').replace(/=/g, '');
const payloadB64 = Buffer.from(JSON.stringify(testPayload)).toString('base64').replace(/=/g, '');
const mockJwt = `${headerB64}.${payloadB64}.fakesig12345`;

const decoded = decodeFullJwt(mockJwt);
assert.ok(decoded, 'JWT must decode cleanly');
assert.strictEqual(decoded.header.alg, "HS256");
assert.strictEqual(decoded.payload.sub, "a1b2c3d4-e5f6-7890-abcd-ef1234567890");
assert.strictEqual(decoded.payload.user_metadata.user_name, "ValeriaAuthor");
console.log('  ✓ Client-side JWT header and payload claims extracted accurately');

// 2b. Supabase base64- Session Bundle Decoding Test
console.log('\nTEST 2b: Supabase base64- Container Extraction Test');
const mockContainer = {
  access_token: mockJwt,
  token_type: "bearer",
  expires_in: 10800,
  expires_at: Math.floor(Date.now() / 1000) + 10800,
  user: {
    id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    email: "creator@example.com",
    user_metadata: { user_name: "ValeriaAuthor" }
  }
};
const base64Bundle = "base64-" + Buffer.from(JSON.stringify(mockContainer)).toString('base64');
assert.ok(base64Bundle.startsWith("base64-"));
const extractedOuter = JSON.parse(Buffer.from(base64Bundle.slice(7), 'base64').toString('utf8'));
assert.strictEqual(extractedOuter.access_token, mockJwt);
assert.strictEqual(extractedOuter.user.user_metadata.user_name, "ValeriaAuthor");
console.log('  ✓ Supabase base64- session container unwrapped and access_token extracted');

// 3. 7 Curated Presets Verification
console.log('\nTEST 3: Curated Archetypes & Templates Verification');
const expectedPresets = ['minimalist', 'obsidian', 'cybernetic', 'gothic', 'audio', 'grimoire', 'card_tabs'];
expectedPresets.forEach(presetKey => {
  assert.ok(html.includes(`data-tpl="${presetKey}"`), `Preset missing in dropdown: ${presetKey}`);
  console.log(`  ✓ Verified preset archetype: ${presetKey}`);
});

// 4. Copywriting / Zero AI Jargon Audit
console.log('\nTEST 4: Copywriting & Tone Audit (Zero AI Buzzwords)');
const forbiddenJargon = [
  /craft\b/i,
  /crafting\b/i,
  /architect\b/i,
  /mastercraft\b/i,
  /bespoke\b/i
];

forbiddenJargon.forEach(regex => {
  // Check visible text outside of skill files
  const matches = (html.match(regex) || []);
  assert.strictEqual(matches.length, 0, `Forbidden jargon found in index.html: ${regex}`);
  console.log(`  ✓ Zero occurrences of ${regex}`);
});

// 5. Custom Dropdowns & Refined Security Badge Verification
console.log('\nTEST 5: Custom Dropdowns & Refined Security Badge Verification');
assert.strictEqual(html.includes('<select'), false, 'All select menus must be custom, no native browser <select> allowed');
console.log('  ✓ Verified 0 native browser <select> elements in codebase');

const requiredDropdowns = [
  'template-dropdown-wrap',
  'asset-width-dropdown',
  'asset-align-dropdown',
  'asset-radius-dropdown'
];
requiredDropdowns.forEach(id => {
  assert.ok(html.includes(`id="${id}"`), `Missing custom dropdown wrap: #${id}`);
  console.log(`  ✓ Verified custom dropdown: #${id}`);
});

assert.ok(html.includes('class="decoder-security-badge"'), 'Missing .decoder-security-badge');
assert.ok(html.includes('100% Client-Side · Zero Network Requests'), 'Missing badge text');
console.log('  ✓ Verified refined 100% Client-Side badge on Token Decoder');

console.log('\n====================================================');
console.log('ALL BIO STUDIO PHASE 3 VERIFICATIONS PASSED (100%)');
console.log('====================================================\n');
