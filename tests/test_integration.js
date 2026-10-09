const assert = require('assert');
const http = require('http');

console.log('====================================================');
console.log('BIO STUDIO PHASE 2 INTEGRATION TEST SUITE');
console.log('====================================================\n');

// 1. URL & UUID Regex Validation
console.log('TEST 1: Character URL & UUID Parsing');
const UUID_REGEX = /([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})/;

function extractUuid(input) {
  const match = input.match(UUID_REGEX);
  return match ? match[1].toLowerCase() : null;
}

const testUrls = [
  { input: "https://janitorai.com/characters/575201cc-52de-404e-b999-4ed4ca98f3e4_sonny-the-grimms", expected: "575201cc-52de-404e-b999-4ed4ca98f3e4" },
  { input: "https://janitorai.com/characters/575201cc-52de-404e-b999-4ed4ca98f3e4", expected: "575201cc-52de-404e-b999-4ed4ca98f3e4" },
  { input: "575201cc-52de-404e-b999-4ed4ca98f3e4", expected: "575201cc-52de-404e-b999-4ed4ca98f3e4" },
  { input: "https://janitorai.com/characters/d17cb25e-e4a8-4447-bcfc-633ca5e10ce0?token=abc", expected: "d17cb25e-e4a8-4447-bcfc-633ca5e10ce0" },
  { input: "https://google.com", expected: null },
  { input: "invalid-uuid-string", expected: null }
];

testUrls.forEach(({ input, expected }, idx) => {
  const result = extractUuid(input);
  assert.strictEqual(result, expected, `Failed for input: ${input}`);
  console.log(`  ✓ Pattern ${idx + 1}: "${input.slice(0, 45)}..." -> ${result || 'rejected (correct)'}`);
});

// 2. JWT Parser & Expiry Verification
console.log('\nTEST 2: JWT Session Token Decoder & Expiry Check');

function parseJwt(tokenStr) {
  if (!tokenStr || typeof tokenStr !== "string") return null;
  const parts = tokenStr.trim().split(".");
  if (parts.length !== 3) return null;
  try {
    const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString('utf8'));
    const now = Math.floor(Date.now() / 1000);
    const exp = payload.exp || 0;
    const isExpired = exp ? exp < now : false;
    return { sub: payload.sub, role: payload.role, exp, isExpired };
  } catch (e) {
    return null;
  }
}

// Sample dummy JWT with future expiration
const futurePayload = Buffer.from(JSON.stringify({ sub: "user-123", role: "authenticated", exp: Math.floor(Date.now() / 1000) + 7200 })).toString('base64');
const dummyJwt = `eyJhbGciOiJIUzI1NiJ9.${futurePayload}.signature`;
const parsedJwt = parseJwt(dummyJwt);

assert.ok(parsedJwt, 'JWT must parse successfully');
assert.strictEqual(parsedJwt.role, 'authenticated');
assert.strictEqual(parsedJwt.isExpired, false);
console.log(`  ✓ JWT parsed successfully: sub=${parsedJwt.sub}, role=${parsedJwt.role}, isExpired=${parsedJwt.isExpired}`);

// 3. Sanitizer Diagnostics & Auto-Fixer
console.log('\nTEST 3: Sanitizer Engine & Auto-Fixer Verification');

function runSanitizer(code) {
  const hasStyle = /<style\b/i.test(code);
  const hasScript = /<script\b/i.test(code);
  const hasPos = /position\s*:\s*(fixed|absolute|sticky)/i.test(code);
  const hasZ = /\bz-index\b/i.test(code);
  const has100vw = /100vw/i.test(code);
  return { hasStyle, hasScript, hasPos, hasZ, has100vw };
}

function autoFix(code) {
  let c = code;
  c = c.replace(new RegExp("<style\\b[^>]*>[\\s\\S]*?<\\/style>", "gi"), "");
  c = c.replace(new RegExp("<script\\b[^>]*>[\\s\\S]*?<\\/script>", "gi"), "");
  c = c.replace(/100vw/gi, "100%");
  c = c.replace(/position\s*:\s*(fixed|absolute|sticky)\s*;?/gi, "");
  c = c.replace(/z-index\s*:\s*[^;"]+\s*;?/gi, "");
  c = c.replace(/\bz-index\b/gi, "");
  c = c.replace(/style="\s*"/gi, "");
  return c.trim();
}

const dirtyHtml = `
<style>.body { color: red; }</style>
<script>alert(1);</script>
<div style="width: 100vw; position: absolute; z-index: 99; color: #fff;">
  <p>Character description with z-index inside styling</p>
</div>
`;

const dirtyDiag = runSanitizer(dirtyHtml);
assert.ok(dirtyDiag.hasStyle, '<style> must be detected');
assert.ok(dirtyDiag.hasScript, '<script> must be detected');
assert.ok(dirtyDiag.hasPos, 'position must be detected');
assert.ok(dirtyDiag.hasZ, 'z-index must be detected');
assert.ok(dirtyDiag.has100vw, '100vw must be detected');
console.log('  ✓ Dirty HTML diagnostics accurately detected all 5 disallowed patterns');

const cleanHtml = autoFix(dirtyHtml);
const cleanDiag = runSanitizer(cleanHtml);
assert.strictEqual(cleanDiag.hasStyle, false, 'Clean HTML must have no style');
assert.strictEqual(cleanDiag.hasScript, false, 'Clean HTML must have no script');
assert.strictEqual(cleanDiag.hasPos, false, 'Clean HTML must have no position');
assert.strictEqual(cleanDiag.hasZ, false, 'Clean HTML must have no z-index');
assert.strictEqual(cleanDiag.has100vw, false, 'Clean HTML must have no 100vw');
console.log('  ✓ Auto-Fixer cleanly sanitized all violations');

// 4. Companion Server Live API Tests
console.log('\nTEST 4: Companion Server Endpoints');

function fetchHttp(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        resolve({ status: res.statusCode, headers: res.headers, body: data });
      });
    }).on('error', reject);
  });
}

async function runServerTests() {
  try {
    const statusRes = await fetchHttp('http://127.0.0.1:8080/api/status');
    assert.strictEqual(statusRes.status, 200);
    const statusJson = JSON.parse(statusRes.body);
    assert.strictEqual(statusJson.status, 'online');
    assert.strictEqual(statusJson.companion, true);
    console.log('  ✓ Companion server status check passed (HTTP 200, online=true)');

    const charRes = await fetchHttp('http://127.0.0.1:8080/api/janitor/characters/575201cc-52de-404e-b999-4ed4ca98f3e4');
    assert.strictEqual(charRes.status, 200);
    const charJson = JSON.parse(charRes.body);
    assert.strictEqual(charJson.id, '575201cc-52de-404e-b999-4ed4ca98f3e4');
    assert.ok(charJson.name, 'Character name must exist');
    console.log(`  ✓ Real character fetch proxy passed: "${charJson.name}" (ID: ${charJson.id})`);

    console.log('\n====================================================');
    console.log('ALL PHASE 2 INTEGRATION TESTS PASSED (100%)');
    console.log('====================================================\n');
  } catch (err) {
    console.error('Server test error:', err);
    process.exit(1);
  }
}

runServerTests();
