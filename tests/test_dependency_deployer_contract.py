from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOYER = (ROOT / "deploy" / "twds-alpha-deploy").read_text(encoding="utf-8")
INSTALLER = (ROOT / "deploy" / "install_dependency_closure_hardening.sh").read_text(encoding="utf-8")


class DependencyDeployerContractTests(unittest.TestCase):
    def test_single_narrow_privileged_entrypoint(self):
        self.assertIn("/usr/local/sbin/twds-alpha-deploy", INSTALLER)
        self.assertNotIn("/etc/sudoers", INSTALLER)
        self.assertNotIn("sudoers.d", INSTALLER)
        self.assertNotIn("NOPASSWD:", INSTALLER)

    def test_fingerprint_gate_precedes_cutover_and_restart(self):
        gate = DEPLOYER.index("DEPENDENCY CLOSURE SAFETY GATE")
        compare = DEPLOYER.index('if [[ "$CANDIDATE_FP" == "$LIVE_FP" ]]')
        cutover = DEPLOYER.index("CUTOVER=1")
        restart = DEPLOYER.index('systemctl restart "$SERVICE"', cutover)
        self.assertLess(gate, compare)
        self.assertLess(compare, cutover)
        self.assertLess(cutover, restart)

    def test_changed_closure_builds_isolated_candidate_before_cutover(self):
        changed = DEPLOYER.index("DEPENDENCY CLOSURE CHANGED")
        venv = DEPLOYER.index('/usr/bin/python3 -m venv "$CANDIDATE_VENV"')
        install = DEPLOYER.index('pip install -r "$SOURCE_TREE/requirements-server.txt"')
        pip_check = DEPLOYER.index("-m pip check")
        runtime = DEPLOYER.index('"$SOURCE_TREE/deploy/verify_auth_install.py"')
        persist = DEPLOYER.index('> "$CANDIDATE_VENV/$FP_NAME"')
        cutover = DEPLOYER.index("CUTOVER=1")
        self.assertLess(changed, venv)
        self.assertLess(venv, install)
        self.assertLess(install, pip_check)
        self.assertLess(pip_check, runtime)
        self.assertLess(runtime, persist)
        self.assertLess(persist, cutover)

    def test_privileged_deployment_consumes_only_root_owned_candidate_source(self):
        self.assertIn("CANDIDATE_ROOT=/var/lib/twds-release-gate/candidates", DEPLOYER)
        self.assertIn('[[ "$RESOLVED_SOURCE_TREE" == "$CANDIDATE_ROOT"/candidate.*/source ]]', DEPLOYER)
        self.assertIn('[[ "$(stat -c %U:%G "$RESOLVED_SOURCE_TREE")" == root:root ]]', DEPLOYER)

        candidate_inputs = (
            'fingerprint "$SOURCE_TREE"',
            '"$SOURCE_TREE/requirements-server.txt"',
            '"$SOURCE_TREE/deploy/verify_templates.py"',
            '"$SOURCE_TREE/deploy/verify_auth_install.py"',
            '"$SOURCE_TREE/" "$APP_DIR/"',
        )
        for candidate_input in candidate_inputs:
            with self.subTest(candidate_input=candidate_input):
                self.assertIn(candidate_input, DEPLOYER)

        # $STAGE is runner-writable and must never become an input to the
        # root-owned deployer, including for requirements or runtime checks.
        self.assertNotIn("$STAGE", DEPLOYER)

    def test_unchanged_closure_reuses_live_venv(self):
        self.assertIn("dependency closure unchanged; validated live venv will be reused", DEPLOYER)
        self.assertIn("Venv: existing validated environment reused", DEPLOYER)

    def test_fingerprint_is_persisted_with_validated_venv(self):
        self.assertIn("FP_NAME=.twds_requirements_fingerprint", DEPLOYER)
        self.assertIn('chmod 0444 "$CANDIDATE_VENV/$FP_NAME"', DEPLOYER)
        self.assertIn('printf \'%s\\n\' "$LIVE_FP" > "$VENV/$FP_NAME"', INSTALLER)
        self.assertIn('chmod 0444 "$VENV/$FP_NAME"', INSTALLER)

    def test_rollback_restores_code_and_previous_venv(self):
        self.assertIn("DEPLOYMENT FAILED - ROLLING BACK", DEPLOYER)
        self.assertIn('rsync -a --delete --exclude=\'instance/\' "$BACKUP_DIR/app/" "$APP_DIR/"', DEPLOYER)
        self.assertIn('ln -s "$OLD_VENV_TARGET" "$VENV_LINK"', DEPLOYER)
        self.assertIn("ROLLBACK SUCCESSFUL", DEPLOYER)

    def test_installer_does_not_rebuild_or_restart_current_venv(self):
        self.assertNotIn("python3 -m venv", INSTALLER)
        self.assertNotIn("pip install", INSTALLER)
        self.assertNotIn("systemctl restart", INSTALLER)
        self.assertIn('"$VENV/bin/python" -m pip check', INSTALLER)
        self.assertIn("LIVE_VENV_REBUILT=0", INSTALLER)
        self.assertIn("SERVICE_RESTARTED=0", INSTALLER)

    def test_no_systemd_immutability_weakening(self):
        combined = DEPLOYER + "\n" + INSTALLER
        self.assertNotIn("ProtectSystem=false", combined)
        self.assertNotIn("ProtectSystem=off", combined)
        self.assertNotIn("ReadWritePaths=/opt/totalrodesign/app", combined)


if __name__ == "__main__":
    unittest.main()
