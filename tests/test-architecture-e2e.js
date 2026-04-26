const scanner = require('./lib/core/architecture-scanner');
const creator = require('./lib/task/creator');
const gateManager = require('./lib/quality/gate-manager');

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

console.log("\n=== 3. Testing M11 Architecture Gate Rejection (Score: 85) ===");
const badContext = {
    metrics: { matchRate: 95, architectureCompliance: 85 }
};
const gateResultBad = gateManager.checkGate('design', badContext);
console.log("Bad Architecture Score (85) => Status:", gateResultBad.status);
console.log("Details:", JSON.stringify(gateResultBad.details, null, 2));

console.log("\n=== 4. Testing M11 Architecture Gate Approval (Score: 100) ===");
const goodContext = {
    metrics: { matchRate: 95, architectureCompliance: 100 }
};
const gateResultGood = gateManager.checkGate('design', goodContext);
console.log("Good Architecture Score (100) => Status:", gateResultGood.status);
console.log("Details:", JSON.stringify(gateResultGood.details, null, 2));

console.log("\n✅ E2E Simulation Completed!");
