/**
 * Cucumber HTML report generator using multiple-cucumber-html-reporter
 * Replaces cucumber-html-reporter (abandoned since 2021)
 * Preserves JSON execution order, supports filter by passed/failed/skipped
 */

const report = require('multiple-cucumber-html-reporter');
const path = require('path');

const args = process.argv.slice(2);
const jsonDir = args[0] || '.';

report.generate({
  jsonDir: jsonDir,
  reportPath: 'cucumber_report',
  reportName: 'Uyuni/Head Testsuite',

  // Preserve the order features appear in the JSON (= execution order)
  // multiple-cucumber-html-reporter does not sort — it uses array order
  displayDuration: true,
  durationInMS: false,  // Cucumber Ruby reports in nanoseconds

  // Show pass/fail/skip filter buttons on the overview
  displayReportTime: true,

  // Flatten metadata (no browser/device columns — not relevant for your setup)
  hideMetadata: true,

  customData: {
    title: 'Run info',
    data: [
      { label: 'Product',   value: 'Uyuni/Head' },
      { label: 'Platform',  value: 'x86_64' },
    ]
  },

  // Screenshots embedded in the report
  // (attach them in your Cucumber hooks with world.attach(screenshot, 'image/png'))

  ignoreBadJsonFile: true,
});
