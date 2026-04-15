#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

function getConfig() {
  let url = process.env.OPENPROJECT_URL || process.env.openproject_url || process.env.openproject_mcp_url;
  let apiKey = process.env.OPENPROJECT_API_KEY || process.env.openproject_api_key;

  const possiblePaths = [
    path.join(process.cwd(), '.rkit', 'config.json'),
    path.join(process.cwd(), '.env'),
    path.join(__dirname, '..', '.rkit', 'config.json'),
    path.join(__dirname, '..', '.env')
  ];

  for (const p of possiblePaths) {
    if (url && apiKey) break;
    if (!fs.existsSync(p)) continue;

    try {
      if (p.endsWith('.json')) {
        const cfg = JSON.parse(fs.readFileSync(p, 'utf8'));
        if (!url) url = cfg.openproject_url || cfg.openproject_mcp_url;
        if (!apiKey) apiKey = cfg.openproject_api_key;
      } else if (p.endsWith('.env')) {
        const lines = fs.readFileSync(p, 'utf8').split('\n');
        for (const line of lines) {
          if (line.trim().startsWith('#')) continue;
          if (!url && line.includes('OPENPROJECT_URL=')) url = line.split('=')[1].trim();
          if (!apiKey && line.includes('OPENPROJECT_API_KEY=')) apiKey = line.split('=')[1].trim();
        }
      }
    } catch(e) {}
  }

  if (url && url.endsWith('/')) url = url.slice(0, -1);
  return { url, apiKey };
}

async function fetchOp(url, apiKey, endpoint) {
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Basic ' + Buffer.from(`apikey:${apiKey}`).toString('base64')
  };
  const res = await fetch(`${url}${endpoint}`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function main() {
  const { url, apiKey } = getConfig();
  if (!url || !apiKey) {
    console.error('❌ [Rkit Standup] OP URL or API KEY not configured.');
    process.exit(1);
  }

  console.log('🔄 Gathering data for your Standup Report...\n');

  try {
    // 1. Fetch Today's Tasks: Assignee = me, Status = Open
    const openFilter = encodeURIComponent(JSON.stringify([
      { "assignee": { "operator": "=", "values": ["me"] } },
      { "status": { "operator": "o", "values": [] } } // 'o' means open
    ]));
    const openData = await fetchOp(url, apiKey, `/api/v3/work_packages?filters=${openFilter}&pageSize=50`);

    // 2. Fetch Yesterday's Closed Tasks: Assignee = me, Status = Closed, Updated last 2 days
    const closedFilter = encodeURIComponent(JSON.stringify([
      { "assignee": { "operator": "=", "values": ["me"] } },
      { "status": { "operator": "c", "values": [] } }, // 'c' means closed
      { "updatedAt": { "operator": ">t-", "values": ["2"] } }
    ]));
    const closedData = await fetchOp(url, apiKey, `/api/v3/work_packages?filters=${closedFilter}&pageSize=50`);

    // 3. Fetch Git Commits from yesterday to today
    let gitCommits = '';
    try {
      const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];
      gitCommits = execSync(`git log --since="${yesterday}" --pretty=format:"- %s" --no-merges`, { stdio: 'pipe' }).toString().trim();
    } catch(e) {
      gitCommits = "- (No commits since yesterday)";
    }
    if (!gitCommits) gitCommits = "- (No commits since yesterday)";

    // =============== RENDER MARKDOWN REPORT ==================
    console.log('======================================================');
    console.log(`🎙️ DAILY STANDUP REPORT (${new Date().toLocaleDateString()})`);
    console.log('======================================================\n');

    console.log('## ⏪ 어제 완료한 일 (Yesterday)');
    if (closedData._embedded?.elements?.length > 0) {
      closedData._embedded.elements.forEach(wp => {
        console.log(`- [OP#${wp.id}] ${wp.subject} ✅`);
      });
    } else {
      console.log('- [OP에서 완료된 티켓이 없습니다]');
    }
    console.log('');
    console.log('**최근 커밋 내역:**');
    console.log(gitCommits);
    console.log('\n----------------------------------------\n');

    console.log('## ⏩ 오늘 할 일 (Today)');
    if (openData._embedded?.elements?.length > 0) {
      openData._embedded.elements.forEach(wp => {
        let typeInfo = '';
        if (wp._links.type?.title) typeInfo = `[${wp._links.type.title}] `;
        console.log(`- [OP#${wp.id}] ${typeInfo}${wp.subject} 🏃`);
      });
    } else {
      console.log('- [OP상 나에게 할당된 진행 중 태스크가 없습니다]');
    }
    console.log('\n----------------------------------------\n');

    console.log('## 🚧 블로커 (Blockers / Issues)');
    console.log('- 없음 (특이사항 기재)');
    console.log('');
    console.log('======================================================');

  } catch (err) {
    console.error('❌ [Rkit Standup] Failed to generate standup report:', err.message);
  }
}

main();
