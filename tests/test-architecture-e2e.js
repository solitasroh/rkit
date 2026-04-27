const scanner = require('../lib/core/architecture-scanner');
const creator = require('../lib/task/creator');
const gateManager = require('../lib/quality/gate-manager');

console.log("=== 1. Testing Architecture Scanner ===");
const map = scanner.scanArchitecture();
if (map.zeroCodebase) {
  console.log("Zero Codebase detected. Refs path will be provided.");
  console.log(scanner.formatArchitectureForPrompt(map));
} else {
  console.log(`Found ${map.modules.length} modules!`);
  console.log(scanner.formatArchitectureForPrompt(map).substring(0, 500) + '...\n(truncated)');
}

console.log("\n=== 2. Testing Prompt Context Injection (Design Phase) ===");
const guidance = creator.generateTaskGuidance('design', 'user-validation');
console.log(guidance);

// NOTE: gate-manager.checkGate() returns { verdict: 'pass'|'retry'|'fail', ... }.
// Earlier revisions logged a non-existent .status field and lacked assertions,
// so this E2E always exited 0 regardless of the gate result. Both cases below
// now assert the verdict explicitly and fail the script on mismatch.

console.log("\n=== 3. Testing M11 Architecture Gate Rejection (Score: 85) ===");
const badContext = {
    // designCompleteness/conventionCompliance pass thresholds, but
    // architectureCompliance (85 < 90) must trigger a non-pass verdict.
    metrics: { designCompleteness: 90, conventionCompliance: 80, architectureCompliance: 85 }
};
const gateResultBad = gateManager.checkGate('design', badContext);
console.log("Bad Architecture Score (85) => Verdict:", gateResultBad.verdict);
console.log("Details:", JSON.stringify(gateResultBad.details, null, 2));
if (gateResultBad.verdict === 'pass') {
    console.error("FAIL: bad context with architectureCompliance=85 should NOT pass.");
    process.exitCode = 1;
}

console.log("\n=== 4. Testing M11 Architecture Gate Approval (Score: 100) ===");
const goodContext = {
    // All three Design-phase metrics must clear their thresholds for verdict='pass'.
    metrics: { designCompleteness: 90, conventionCompliance: 80, architectureCompliance: 100 }
};
const gateResultGood = gateManager.checkGate('design', goodContext);
console.log("Good Architecture Score (100) => Verdict:", gateResultGood.verdict);
console.log("Details:", JSON.stringify(gateResultGood.details, null, 2));
if (gateResultGood.verdict !== 'pass') {
    console.error("FAIL: good context with all Design-phase metrics ≥ thresholds should pass; got '" + gateResultGood.verdict + "'.");
    process.exitCode = 1;
}

if (process.exitCode === 1) {
    console.error("\n❌ E2E Simulation FAILED — see assertion errors above.");
} else {
    console.log("\n✅ E2E Simulation Completed!");
}
