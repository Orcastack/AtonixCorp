const fs = require('fs');
const path = require('path');

const rootDir = path.resolve(__dirname, '..');
const baselinePath = path.join(rootDir, 'ledgora-public-standards-baseline.json');
const writeBaseline = process.argv.includes('--write-baseline');

const allowedHexValues = new Set(['000000', 'ffffff', 'ee6c4d', '000', 'fff']);
const allowedRgbTriples = new Set(['0,0,0', '255,255,255', '238,108,77']);
const allowedSpacingValues = new Set(['0', '4', '8', '12', '16', '24', '32', '48']);
const fileExtensions = new Set(['.css', '.js', '.jsx']);

const targets = [
  'src/styles/globals.css',
  'src/styles/pages.css',
  'src/styles/public-site.css',
  'src/components/ui',
  'src/components/Layout',
  'src/components/WorkspaceLayout',
  'src/components/Header',
  'src/components/Footer',
  'src/components/footer',
  'src/pages/Landing',
  'src/pages/Product',
  'src/pages/Features',
  'src/pages/Pricing',
  'src/pages/About',
  'src/pages/Support',
  'src/pages/HelpCenter',
  'src/pages/Contact',
  'src/pages/Privacy',
  'src/pages/GlobalTax',
  'src/pages/CLIDocs',
  'src/pages/Deployment',
];

function collectFiles(targetPath, results) {
  const fullPath = path.join(rootDir, targetPath);
  if (!fs.existsSync(fullPath)) {
    return;
  }

  const stat = fs.statSync(fullPath);
  if (stat.isDirectory()) {
    for (const entry of fs.readdirSync(fullPath)) {
      collectFiles(path.join(targetPath, entry), results);
    }
    return;
  }

  if (fileExtensions.has(path.extname(fullPath))) {
    results.push(fullPath);
  }
}

function lineNumberFromIndex(text, index) {
  return text.slice(0, index).split('\n').length;
}

function addFinding(findings, filePath, line, rule, snippet) {
  const relativePath = path.relative(rootDir, filePath).replace(/\\/g, '/');
  const normalizedSnippet = snippet.trim().replace(/\s+/g, ' ');
  findings.push({
    key: `${relativePath}|${rule}|${line}|${normalizedSnippet}`,
    file: relativePath,
    line,
    rule,
    snippet: normalizedSnippet,
  });
}

function scanCss(findings, filePath, text) {
  const hexRegex = /#([0-9a-fA-F]{3,8})/g;
  for (const match of text.matchAll(hexRegex)) {
    const value = match[1].toLowerCase();
    if (!allowedHexValues.has(value)) {
      addFinding(findings, filePath, lineNumberFromIndex(text, match.index), 'forbidden-hex-color', match[0]);
    }
  }

  const rgbRegex = /(rgba?|hsla?)\(([^)]+)\)/g;
  for (const match of text.matchAll(rgbRegex)) {
    if (match[2].includes('var(')) {
      continue;
    }

    const numericParts = match[2]
      .split(',')
      .map((part) => part.trim())
      .slice(0, 3)
      .map((part) => Number.parseInt(part, 10));

    if (numericParts.length < 3 || numericParts.some(Number.isNaN)) {
      continue;
    }

    const triple = numericParts.join(',');
    if (!allowedRgbTriples.has(triple)) {
      addFinding(findings, filePath, lineNumberFromIndex(text, match.index), 'forbidden-rgb-color', match[0]);
    }
  }

  const bannedPropertyRegex = /\b(box-shadow|text-shadow|backdrop-filter)\s*:/g;
  for (const match of text.matchAll(bannedPropertyRegex)) {
    addFinding(findings, filePath, lineNumberFromIndex(text, match.index), 'forbidden-effect', match[0]);
  }

  const clampRegex = /\bclamp\(/g;
  for (const match of text.matchAll(clampRegex)) {
    addFinding(findings, filePath, lineNumberFromIndex(text, match.index), 'forbidden-clamp', 'clamp(');
  }

  const pillRadiusRegex = /border-radius\s*:\s*999px/g;
  for (const match of text.matchAll(pillRadiusRegex)) {
    addFinding(findings, filePath, lineNumberFromIndex(text, match.index), 'forbidden-pill-radius', match[0]);
  }

  const spacingRegex = /\b(?:padding(?:-(?:top|right|bottom|left))?|margin(?:-(?:top|right|bottom|left))?|gap|row-gap|column-gap)\s*:\s*([^;]+);/g;
  for (const match of text.matchAll(spacingRegex)) {
    const value = match[1];
    const pxMatches = [...value.matchAll(/(-?\d+(?:\.\d+)?)px/g)];
    const invalidValue = pxMatches.find((pxMatch) => !allowedSpacingValues.has(pxMatch[1]));

    if (invalidValue) {
      addFinding(findings, filePath, lineNumberFromIndex(text, match.index), 'off-grid-spacing', match[0]);
    }
  }
}

function scanJs(findings, filePath, text) {
  const inlineStyleRegex = /style\s*=\s*\{\{/g;
  for (const match of text.matchAll(inlineStyleRegex)) {
    addFinding(findings, filePath, lineNumberFromIndex(text, match.index), 'inline-style', 'style={{');
  }

  const hexRegex = /#([0-9a-fA-F]{3,8})/g;
  for (const match of text.matchAll(hexRegex)) {
    const value = match[1].toLowerCase();
    if (!allowedHexValues.has(value)) {
      addFinding(findings, filePath, lineNumberFromIndex(text, match.index), 'forbidden-hex-color', match[0]);
    }
  }
}

function scanFile(findings, filePath) {
  const text = fs.readFileSync(filePath, 'utf8');
  const extension = path.extname(filePath);

  if (extension === '.css') {
    scanCss(findings, filePath, text);
    return;
  }

  scanJs(findings, filePath, text);
}

function sortFindings(findings) {
  return findings.sort((left, right) => left.key.localeCompare(right.key));
}

const files = [];
for (const target of targets) {
  collectFiles(target, files);
}

const findings = [];
for (const filePath of files) {
  scanFile(findings, filePath);
}

const sortedFindings = sortFindings(findings);

if (writeBaseline) {
  fs.writeFileSync(
    baselinePath,
    JSON.stringify(
      {
        generatedAt: new Date().toISOString(),
        findings: sortedFindings,
      },
      null,
      2,
    ) + '\n',
  );
  console.log(`Wrote Ledgora public standards baseline with ${sortedFindings.length} findings.`);
  process.exit(0);
}

if (!fs.existsSync(baselinePath)) {
  console.error('Ledgora public standards baseline is missing. Run npm run standards:baseline first.');
  process.exit(1);
}

const baseline = JSON.parse(fs.readFileSync(baselinePath, 'utf8'));
const baselineKeys = new Set((baseline.findings || []).map((finding) => finding.key));
const newFindings = sortedFindings.filter((finding) => !baselineKeys.has(finding.key));

if (newFindings.length === 0) {
  console.log(`Ledgora public standards check passed. Baseline findings tracked: ${baselineKeys.size}.`);
  process.exit(0);
}

console.error(`Ledgora public standards check failed with ${newFindings.length} new finding(s):`);
for (const finding of newFindings) {
  console.error(`- ${finding.file}:${finding.line} [${finding.rule}] ${finding.snippet}`);
}
process.exit(1);