import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { buildLocalProcessSandboxSpawnTarget as build } from '../../packages/adapter-utils/src/local-process-sandbox.ts';

// These tests construct arguments only. They never execute bwrap or an agent.
const workspace = await fs.mkdtemp(path.join(os.tmpdir(), 'paperclip-bwrap-plan-'));
const aliases = ['/bin', '/sbin', '/lib', '/lib64'];
const saved = { lstat: fs.lstat, realpath: fs.realpath, readlink: fs.readlink };
const input = {
  executable: process.execPath, args: ['--version'], cwd: workspace,
  options: { workspaceDir: workspace, filesystemScope: 'workspace', networkScope: 'deny' },
};
const triple = (a, flag, src, dst) =>
  a.findIndex((v, i) => v === flag && a[i + 1] === src && a[i + 2] === dst);

async function plan(mode) {
  fs.lstat = async p => {
    if (!aliases.includes(p)) return saved.lstat(p);
    if (mode === 'missing-lib64' && p === '/lib64') {
      throw Object.assign(new Error('absent test alias'), { code: 'ENOENT' });
    }
    return { isSymbolicLink: () => mode !== 'unmerged' };
  };
  fs.realpath = async p => aliases.includes(p)
    ? (mode === 'outside-target' && p === '/bin' ? '/opt/private/bin' : '/usr' + p)
    : saved.realpath(p);
  fs.readlink = async p => aliases.includes(p)
    ? (mode === 'outside-target' && p === '/bin' ? '/opt/private/bin'
       : (mode === 'absolute' ? '/usr' : 'usr') + p)
    : saved.readlink(p);
  try { return await build(input); }
  finally { Object.assign(fs, saved); }
}

try {
  for (const mode of ['merged', 'absolute', 'unmerged', 'missing-lib64']) {
    const result = await plan(mode);
    const end = result.args.indexOf('--');
    assert.ok(end > 0);
    const a = result.args.slice(0, end);
    const usr = triple(a, '--ro-bind', '/usr', '/usr');
    assert.ok(usr >= 0, '/usr must be read-only');

    for (const alias of aliases) {
      if (mode === 'missing-lib64' && alias === '/lib64') {
        assert.equal(triple(a, '--ro-bind', alias, alias), -1);
        assert.equal(triple(a, '--symlink', 'usr' + alias, alias), -1);
      } else if (mode === 'unmerged') {
        assert.ok(triple(a, '--ro-bind', alias, alias) > usr);
        assert.equal(triple(a, '--symlink', 'usr' + alias, alias), -1);
      } else {
        const target = (mode === 'absolute' ? '/usr' : 'usr') + alias;
        assert.ok(triple(a, '--symlink', target, alias) > usr, alias + ' must follow /usr');
        assert.equal(triple(a, '--ro-bind', alias, alias), -1, 'no bind over alias');
      }
    }

    for (const flag of [
      '--die-with-parent', '--new-session', '--unshare-pid',
      '--unshare-ipc', '--unshare-uts', '--unshare-net'
    ]) {
      assert.ok(a.includes(flag), 'confinement flag removed: ' + flag);
    }
    assert.equal(triple(a, '--bind', '/', '/'), -1);
    assert.equal(triple(a, '--bind', '/usr', '/usr'), -1);
    assert.ok(triple(a, '--bind', workspace, workspace) >= 0);
    assert.equal(result.args[end + 1], process.execPath, 'stdio launcher must remain');
    console.log('PASS layout=' + mode + '; confinement arguments preserved');
  }

  await assert.rejects(() => plan('outside-target'), /Unsupported sandbox system alias/);
  console.log('PASS unsupported system alias fails closed');

  await assert.rejects(() => build({
    ...input,
    options: {
      ...input.options,
      extraPaths: [{ path: '/outside-workspace', access: 'rw' }]
    }
  }), /outbound restore mapping/);
  console.log('PASS unrelated writable path remains rejected');
} finally {
  Object.assign(fs, saved);
  await fs.rm(workspace, { recursive: true, force: true });
}
