/**
 * https://github.com/WasiqB/multiple-cucumber-html-reporter
 * Preserves execution order by injecting a sequence number into feature names
 * before generating the report, since the library always sorts alphabetically.
 */

const report = require('multiple-cucumber-html-reporter');
const fs = require('fs');
const path = require('path');
const os = require('os');

const args = process.argv.slice(2);
const jsonDir = args[0] || '.';

// Read all Cucumber JSON files in the directory.
// Filenames contain timestamps (e.g. output_20260429143645-sanity_check.json)
// so lexicographic sort == chronological == execution order.
if (!fs.existsSync(jsonDir) || !fs.statSync(jsonDir).isDirectory()) {
  console.error(`Results directory not found or not a directory: ${jsonDir}`);
  process.exit(1);
}
const jsonFiles = fs.readdirSync(jsonDir)
  .filter(f => f.match(/^output_.*\.json$/))
  .sort()
  .map(f => path.join(jsonDir, f));

if (jsonFiles.length === 0) {
  console.error(`No output_*.json files found in: ${jsonDir}`);
  process.exit(1);
}

// Load and merge all features, injecting a zero-padded sequence number
// into each feature name so alphabetical sort == execution order.
let sequenceNumber = 0;
const allFeatures = [];

for (const file of jsonFiles) {
  try {
    const features = JSON.parse(fs.readFileSync(file, 'utf8'));
    for (const feature of features) {
      sequenceNumber++;
      const pad = String(sequenceNumber).padStart(4, '0');
      feature.name = `${pad} - ${feature.name}`;
    }
    allFeatures.push(...features);
  } catch (e) {
    console.warn(`Skipping bad JSON file: ${file} — ${e.message}`);
  }
}

console.log(`Loaded ${allFeatures.length} features from ${jsonFiles.length} JSON files.`);

// Write the merged file into a dedicated temp directory.
// This avoids passing both jsonDir (original files) and jsonFile (merged file)
// to the reporter simultaneously, which caused duplicate un-numbered entries.
// The library requires jsonDir to be set, so we point it at the temp dir
// that contains only our single ordered merged file.
const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'cucumber-report-'));
const mergedJsonPath = path.join(tmpDir, 'ordered_report.json');
fs.writeFileSync(mergedJsonPath, JSON.stringify(allFeatures));

try {
  report.generate({
    jsonDir: tmpDir,        // only our merged file lives here — no duplicates
    jsonFile: mergedJsonPath,
    reportPath: 'cucumber_report',
    reportName: 'Uyuni/Head Testsuite',
    displayDuration: true,
    durationInMS: false,
    displayReportTime: true,
    hideMetadata: true,
    ignoreBadJsonFile: true,
    customData: {
      title: 'Run info',
      data: [
        { label: 'Product',  value: 'Uyuni/Head' },
        { label: 'Platform', value: 'x86_64' },
      ]
    }
  });
} finally {
  // Always clean up the temp directory
  fs.rmSync(tmpDir, { recursive: true, force: true });
}
