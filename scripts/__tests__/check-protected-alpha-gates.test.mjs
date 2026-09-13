import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { validateProtectedAlphaGates } from '../check-protected-alpha-gates.mjs';

const root = path.resolve(import.meta.dirname, '../..');

function fixtureRoot() {
  const fixture = fs.mkdtempSync(path.join(os.tmpdir(), 'protected-alpha-gates-'));
  fs.cpSync(path.join(root, '.github'), path.join(fixture, '.github'), { recursive: true });
  return fixture;
}

test('protected Alpha workflow gates pass for repository workflows', () => {
  assert.doesNotThrow(() => validateProtectedAlphaGates(root));
});

test('workflow gate checker rejects a fail-open required e2e aggregate', () => {
  const fixture = fixtureRoot();
  try {
    const workflow = path.join(fixture, '.github/workflows/pr-trusted.yml');
    fs.writeFileSync(
      workflow,
      fs.readFileSync(workflow, 'utf8').replace(
        /(  e2e:\n[\s\S]*?    if:) \$\{\{ always\(\) \}\}/,
        '$1 ${{ success() }}',
      ),
    );
    assert.throws(() => validateProtectedAlphaGates(fixture), /must run even when shards fail or are skipped/);
  } finally {
    fs.rmSync(fixture, { recursive: true, force: true });
  }
});

test('workflow gate checker rejects a dispatch path that does not run the validator', () => {
  const fixture = fixtureRoot();
  try {
    const workflow = path.join(fixture, '.github/workflows/e2e.yml');
    fs.writeFileSync(workflow, fs.readFileSync(workflow, 'utf8').replace('run: exec pnpm run test:e2e', 'run: echo dispatched'));
    assert.throws(() => validateProtectedAlphaGates(fixture), /must invoke the e2e validator/);
  } finally {
    fs.rmSync(fixture, { recursive: true, force: true });
  }
});

test('workflow gate checker rejects a mutable OIDC checkout', () => {
  const fixture = fixtureRoot();
  try {
    fs.writeFileSync(
      path.join(fixture, '.github/workflows/agent-runtime-images.yml'),
      fs.readFileSync(path.join(fixture, '.github/workflows/agent-runtime-images.yml'), 'utf8')
        .replace('actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1', 'actions/checkout@v7'),
    );
    assert.throws(() => validateProtectedAlphaGates(fixture), /unpinned checkout/);
  } finally {
    fs.rmSync(fixture, { recursive: true, force: true });
  }
});
