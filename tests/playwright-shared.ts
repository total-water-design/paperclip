/**
 * Chromium launch settings for Paperclip-owned browser acceptance and evidence
 * suites. TOT-3626: agents run inside bwrap//&unpriv_bwrap, which denies the
 * nested capability Chromium needs for its own sandbox. The outer agent
 * sandbox remains the security boundary, so these flags are intentionally
 * limited to test configurations that load Paperclip's own application.
 */
export const chromiumLaunchOptions = {
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
};
