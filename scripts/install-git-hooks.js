const fs = require('fs');
const path = require('path');

const hookTarget = path.join(__dirname, '..', '.git', 'hooks', 'commit-msg');

const hookScript = `#!/usr/bin/env node

const fs = require('fs');
const { execSync } = require('child_process');

try {
  // 1. Get current branch name
  const branchName = execSync('git branch --show-current', { stdio: 'pipe' }).toString().trim();

  // 2. Check if it's an OP-related branch (feature/op-*, bugfix/op-*, or just containing op-* / op_*)
  if (!/(?:op[-_]\\d+)/i.test(branchName)) {
    // Not an OP ticket branch. Bypass the check.
    process.exit(0);
  }

  // 3. Read the commit message
  const msgFile = process.argv[2];
  if (!msgFile || !fs.existsSync(msgFile)) {
    console.error('❌ [Rkit] Error: Could not find commit message file.');
    process.exit(1);
  }
  const msgContent = fs.readFileSync(msgFile, 'utf8');

  // 4. Validate presence of [OP#<number>] anywhere in the message. Case insensitive.
  // We don't enforce strict matching of branch ID to allow sub-tasks to be committed in epic branches.
  const opTagRegex = /\\[OP#\\d+\\]/i;

  if (!opTagRegex.test(msgContent)) {
    console.error('\\n======================================================');
    console.error('❌ [Rkit OP-Hook] Commit Blocked!');
    console.error('======================================================');
    console.error('You are working on an OpenProject branch: ' + branchName);
    console.error('However, no OpenProject Ticket Tag was found in your commit message.');
    console.error('Please include a tag like [OP#123] in your commit message.');
    console.error('If you are using #time to log hours, remember to include it as well (e.g., [OP#123] feat: add login #time 2h).');
    console.error('======================================================\\n');
    process.exit(1);
  }

  // Valid OP Tag found! Proceed.
  process.exit(0);

} catch (err) {
  console.error('❌ [Rkit] Unexpected error inside commit-msg hook:', err.message);
  process.exit(1); // Block on unexpected errors to be safe, or 0 if we want to bypass softly
}
`;

function install() {
  const gitHooksDir = path.dirname(hookTarget);
  if (!fs.existsSync(gitHooksDir)) {
    console.error('❌ Git hooks directory not found. Are you in a git repository?');
    process.exit(1);
  }

  const postCommitTarget = path.join(__dirname, '..', '.git', 'hooks', 'post-commit');
  const postCommitScript = `#!/usr/bin/env node
const { execSync } = require('child_process');
const path = require('path');
try {
  execSync('node ' + path.join('scripts', 'op-sync-time.js'), { stdio: 'inherit' });
} catch (e) { /* non-blocking */ }
`;

  console.log('🔄 Installing Rkit OpenProject commit-msg Hook...');
  fs.writeFileSync(hookTarget, hookScript, { encoding: 'utf8', mode: 0o755 });
  console.log('✅ Successfully installed commit-msg hook.');

  console.log('🔄 Installing Rkit OpenProject post-commit Hook (Time Sync)...');
  fs.writeFileSync(postCommitTarget, postCommitScript, { encoding: 'utf8', mode: 0o755 });
  console.log('✅ Successfully installed post-commit hook.');
}

install();
