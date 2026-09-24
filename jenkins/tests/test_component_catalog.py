import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from jenkins.python.change_detection.detector import classify, render_env
from jenkins.python.release_plan import build_plan


ROOT = Path(__file__).resolve().parents[2]
CATALOG = json.loads((ROOT / "jenkins/config/components.json").read_text())


class DetectorContractTest(unittest.TestCase):
    def test_documentation_only_is_unchanged(self):
        selected, unmapped = classify(
            CATALOG,
            ["docs/jenkins.md", "README.md", "architecture.excalidraw"],
            [],
        )
        self.assertEqual([], selected)
        self.assertEqual([], unmapped)
        self.assertIn("CHANGED_COMPONENTS=unchanged", render_env(CATALOG, selected))
        self.assertEqual([], build_plan(CATALOG, selected)["images"])
        self.assertEqual([], build_plan(CATALOG, selected)["deploy_units"])

    def test_unknown_runtime_path_fails_closed(self):
        selected, unmapped = classify(CATALOG, ["services/new/runtime.py"], [])
        self.assertEqual([], selected)
        self.assertEqual(["services/new/runtime.py"], unmapped)

    def test_frontend_only(self):
        selected, unmapped = classify(CATALOG, ["apps/frontend/app/page.tsx"], [])
        self.assertEqual(["frontend"], selected)
        self.assertEqual([], unmapped)
        self.assertEqual(
            {"components": ["frontend"], "images": ["frontend"], "deploy_units": ["frontend"]},
            build_plan(CATALOG, selected),
        )

    def test_migration_adds_backend_gate_and_units(self):
        selected, unmapped = classify(
            CATALOG, ["apps/backend/migrations/versions/revision.py"], []
        )
        self.assertEqual(["backend", "migration"], selected)
        self.assertEqual([], unmapped)
        plan = build_plan(CATALOG, selected)
        self.assertEqual(["backend"], plan["images"])
        self.assertEqual(["migrate", "import-data", "backend"], plan["deploy_units"])

    def test_ci_config_only_has_no_product_release(self):
        selected, unmapped = classify(
            CATALOG, ["Jenkinsfile", "docker/jenkins-agent/Dockerfile"], []
        )
        self.assertEqual(["ci_config"], selected)
        self.assertEqual([], unmapped)
        self.assertIn("CI_PROFILE_CONTRACTS=true", render_env(CATALOG, selected))
        self.assertEqual([], build_plan(CATALOG, selected)["images"])
        self.assertEqual([], build_plan(CATALOG, selected)["deploy_units"])

    def test_model_prompt_only_runs_contract_profile(self):
        selected, unmapped = classify(CATALOG, ["pipelines/training/train_hf.py"], [])
        self.assertEqual(["model_prompt"], selected)
        self.assertEqual([], unmapped)
        self.assertIn("CI_PROFILE_MODEL_CONTRACT=true", render_env(CATALOG, selected))
        self.assertEqual([], build_plan(CATALOG, selected)["images"])

    def test_force_component_and_deterministic_order(self):
        selected, unmapped = classify(
            CATALOG, ["apps/frontend/app/page.tsx", "apps/backend/app.py"], ["frontend"]
        )
        self.assertEqual(["backend", "frontend"], selected)
        self.assertEqual([], unmapped)

    def test_unknown_forced_component_fails(self):
        with self.assertRaisesRegex(ValueError, "unknown forced component"):
            classify(CATALOG, [], ["missing"])

    def test_shared_backend_resources_are_deduplicated(self):
        plan = build_plan(CATALOG, ["migration", "backend"])
        self.assertEqual(["backend"], plan["images"])
        self.assertEqual(1, plan["deploy_units"].count("backend"))

    def test_invalid_catalog_reference_fails_closed(self):
        invalid = json.loads(json.dumps(CATALOG))
        invalid["components"]["frontend"]["deploy_units"] = ["misspelled"]
        with self.assertRaisesRegex(ValueError, "invalid catalog references"):
            classify(invalid, ["apps/frontend/app/page.tsx"], [])

    def test_runtime_stack_releases_both_services(self):
        selected, unmapped = classify(CATALOG, ["docker-compose.yml"], [])
        self.assertEqual(["runtime_stack"], selected)
        self.assertEqual([], unmapped)
        plan = build_plan(CATALOG, selected)
        self.assertEqual(["backend", "frontend"], plan["images"])
        self.assertEqual(["backend", "frontend"], plan["deploy_units"])

    def test_every_tracked_non_ignored_path_is_mapped(self):
        paths = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.splitlines()
        _, unmapped = classify(CATALOG, paths, [])
        self.assertEqual([], unmapped)


class DetectorCliTest(unittest.TestCase):
    def test_cli_writes_generated_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "ci@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "CI"], cwd=repo, check=True)
            (repo / "README.md").write_text("base\n")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
            base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()
            (repo / "apps/frontend").mkdir(parents=True)
            (repo / "apps/frontend/page.tsx").write_text("page\n")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "frontend"], cwd=repo, check=True)
            output = repo / ".ci-components.env"
            subprocess.run(
                ["python3", str(ROOT / "jenkins/python/change_detection/detector.py"), base, "HEAD", "--catalog", str(ROOT / "jenkins/config/components.json"), "--output", str(output)],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("CHANGED_COMPONENTS=frontend", output.read_text())

    def test_cli_fails_closed_and_names_unmapped_path(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "ci@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "CI"], cwd=repo, check=True)
            (repo / "README.md").write_text("base\n")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
            base = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                capture_output=True, text=True,
            ).stdout.strip()
            unknown = repo / "services/new/runtime.py"
            unknown.parent.mkdir(parents=True)
            unknown.write_text("runtime\n")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "unknown"], cwd=repo, check=True)
            result = subprocess.run(
                [
                    "python3", str(ROOT / "jenkins/python/change_detection/detector.py"),
                    base, "HEAD", "--catalog",
                    str(ROOT / "jenkins/config/components.json"),
                ],
                cwd=repo,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("unmapped runtime path(s): services/new/runtime.py", result.stderr)

    def test_deleted_runtime_path_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "ci@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "CI"], cwd=repo, check=True)
            runtime = repo / "apps/backend/removed.py"
            runtime.parent.mkdir(parents=True)
            runtime.write_text("runtime\n")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
            base = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                capture_output=True, text=True,
            ).stdout.strip()
            runtime.unlink()
            subprocess.run(["git", "add", "-u"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "delete"], cwd=repo, check=True)
            output = repo / ".ci-components.env"
            subprocess.run(
                [
                    "python3", str(ROOT / "jenkins/python/change_detection/detector.py"),
                    base, "HEAD", "--catalog",
                    str(ROOT / "jenkins/config/components.json"),
                    "--output", str(output),
                ],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("CHANGED_COMPONENTS=backend", output.read_text())

    def test_rename_classifies_both_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "ci@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "CI"], cwd=repo, check=True)
            source = repo / "apps/backend/renamed.py"
            source.parent.mkdir(parents=True)
            source.write_text("runtime\n")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
            base = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                capture_output=True, text=True,
            ).stdout.strip()
            target = repo / "docs/renamed.md"
            target.parent.mkdir(parents=True)
            source.rename(target)
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "rename"], cwd=repo, check=True)
            output = repo / ".ci-components.env"
            subprocess.run(
                [
                    "python3", str(ROOT / "jenkins/python/change_detection/detector.py"),
                    base, "HEAD", "--catalog",
                    str(ROOT / "jenkins/config/components.json"),
                    "--output", str(output),
                ],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("CHANGED_COMPONENTS=backend", output.read_text())


class ReleasePlannerCliTest(unittest.TestCase):
    def test_cli_writes_deterministic_json_and_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            components = temp / "components.env"
            plan = temp / "plan.json"
            environment = temp / "release.env"
            components.write_text("CHANGED_COMPONENTS=backend,migration\n")
            subprocess.run(
                [
                    "python3", str(ROOT / "jenkins/python/release_plan.py"),
                    "--catalog", str(ROOT / "jenkins/config/components.json"),
                    "--components-env", str(components),
                    "--output", str(plan),
                    "--env-output", str(environment),
                ],
                cwd=ROOT,
                check=True,
            )
            self.assertEqual(
                {
                    "components": ["backend", "migration"],
                    "images": ["backend"],
                    "deploy_units": ["migrate", "import-data", "backend"],
                },
                json.loads(plan.read_text()),
            )
            self.assertEqual(
                "RELEASE_IMAGES=backend\n"
                "DEPLOY_UNITS=migrate,import-data,backend\n"
                "HAS_RELEASE=true\n",
                environment.read_text(),
            )


if __name__ == "__main__":
    unittest.main()
