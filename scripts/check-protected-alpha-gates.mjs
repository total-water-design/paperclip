import fs from 'node:fs';
import path from 'node:path';

const checkoutSha = '3d3c42e5aac5ba805825da76410c181273ba90b1';

function read(root, relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8');
}

function jobBlock(workflow, name) {
  const match = workflow.match(new RegExp(`^  ${name}:\\n([\\s\\S]*?)(?=^  [A-Za-z0-9_-]+:|(?![\\s\\S]))`, 'm'));
  if (!match) throw new Error(`missing job: ${name}`);
  return match[0];
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

export function validateProtectedAlphaGates(root) {
  const trusted = read(root, '.github/workflows/pr-trusted.yml');
  const aggregate = jobBlock(trusted, 'e2e');
  assert(/name: e2e/.test(aggregate), 'required e2e aggregate must retain its check name');
  assert(/if: \$\{\{ always\(\) \}\}/.test(aggregate), 'required e2e aggregate must run even when shards fail or are skipped');
  assert(/needs: \[gate, e2e_shards\]/.test(aggregate), 'required e2e aggregate must depend on e2e_shards');
  assert(/test "\$E2E_SHARDS_RESULT" = "success"/.test(aggregate), 'required e2e aggregate must fail unless e2e_shards succeeds');

  const e2e = read(root, '.github/workflows/e2e.yml');
  assert(/^  pull_request:/m.test(e2e), 'e2e workflow must run for pull requests');
  assert(/validation_target:[\s\S]*?protected-alpha/.test(e2e), 'dispatch must expose protected-alpha validation');
  assert(/ref: \$\{\{ inputs\.validation_target == 'protected-alpha' && inputs\.protected_ref \|\| github\.sha \}\}/.test(e2e), 'protected-alpha dispatch must checkout the selected protected ref');
  assert(/test "\$PROTECTED_REF" = 'alpha'/.test(e2e), 'protected-alpha dispatch must reject a non-alpha ref');
  assert(/run: exec pnpm run test:e2e/.test(e2e), 'protected-alpha dispatch must invoke the e2e validator without masking failures');
  assert(!/test:e2e\s*\|\|\s*true/.test(e2e), 'e2e validator failure must not be ignored');

  const workflowDirectory = path.join(root, '.github/workflows');
  const oidcWorkflows = fs.readdirSync(workflowDirectory)
    .filter((name) => /\.ya?ml$/.test(name))
    .map((name) => `.github/workflows/${name}`)
    .filter((relativePath) => /id-token:\s*write/.test(read(root, relativePath)));
  assert(oidcWorkflows.length > 0, 'expected at least one OIDC-bearing workflow to audit');

  for (const relativePath of oidcWorkflows) {
    const workflow = read(root, relativePath);
    const globalPermissions = workflow.match(/^permissions:\n([\s\S]*?)(?=^[A-Za-z]|(?![\s\S]))/m)?.[0] ?? '';
    const oidcSections = /^\s*id-token:\s*write/m.test(globalPermissions)
      ? [workflow]
      : workflow.split(/(?=^  [A-Za-z0-9_-]+:)/m).filter((section) => /id-token:\s*write/.test(section));
    assert(oidcSections.length > 0, `${relativePath} must retain expected OIDC coverage`);
    for (const section of oidcSections) {
      const checkoutRefs = [...section.matchAll(/actions\/checkout@([^\s#]+)/g)].map((match) => match[1]);
      assert(checkoutRefs.length > 0, `${relativePath} has an OIDC-bearing scope without checkout`);
      assert(checkoutRefs.every((ref) => ref === checkoutSha), `${relativePath} has an OIDC-bearing scope with an unpinned checkout`);
    }
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  try {
    validateProtectedAlphaGates(process.cwd());
    console.log('protected-alpha workflow gate assertions passed');
  } catch (error) {
    console.error(`protected-alpha workflow gate assertion failed: ${error.message}`);
    process.exitCode = 1;
  }
}
