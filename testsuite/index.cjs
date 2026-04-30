/**
 * https://github.com/WasiqB/multiple-cucumber-html-reporter
 * Replaces cucumber-html-reporter (abandoned since 2021).
 * Preserves JSON execution order, supports filter by passed/failed/skipped.
 */

const report = require('multiple-cucumber-html-reporter');
const report = require('multiple-cucumber-html-reporter');
const path = require('path');

// Read command-line arguments
const args = process.argv.slice(2);
const jsonDir = args[0] || '.'; // Default to current directory if no argument provided

report.generate({
  jsonDir: jsonDir,
  // Output to cucumber_report/ — the reporter creates index.html inside this folder.
  // The Rakefile copies cucumber_report/index.html as cucumber_report.html into result_folder.
  reportPath: 'cucumber_report',
  reportName: 'Uyuni/Head Testsuite',

  // Preserve the order features appear in the JSON (= execution order).
  // multiple-cucumber-html-reporter does not sort — it uses the JSON array order.
  displayDuration: true,
  // Cucumber Ruby reports durations in nanoseconds (not milliseconds)
  durationInMS: false,

  displayReportTime: true,

  // No browser/device metadata columns — not relevant for this setup
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
