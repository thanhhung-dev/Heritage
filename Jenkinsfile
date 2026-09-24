pipeline {
  agent any
  options { skipDefaultCheckout(true); timestamps(); disableConcurrentBuilds() }
  environment { DEPLOY_BRANCH = 'main' }
  stages {
    stage('Checkout') { steps { checkout scm; script { env.GIT_COMMIT = sh(script: 'git rev-parse HEAD', returnStdout: true).trim() } } }
    stage('Detect changes') {
      steps { script {
        def base
        if (env.CHANGE_TARGET) {
          sh 'git fetch --no-tags origin "+refs/heads/${CHANGE_TARGET}:refs/remotes/origin/${CHANGE_TARGET}"'
          base = sh(script: 'git merge-base HEAD "origin/${CHANGE_TARGET}"', returnStdout: true).trim()
        } else {
          def previous = env.GIT_PREVIOUS_SUCCESSFUL_COMMIT ?: env.GIT_PREVIOUS_COMMIT ?: ''
          withEnv(["CANDIDATE_BASE=${previous}"]) {
            base = sh(script: 'if test -n "$CANDIDATE_BASE" && git cat-file -e "$CANDIDATE_BASE^{commit}" 2>/dev/null; then printf "%s" "$CANDIDATE_BASE"; else git rev-parse HEAD^ 2>/dev/null || git hash-object -t tree /dev/null; fi', returnStdout: true).trim()
          }
        }
        def detected = sh(script: "jenkins/change-detection.sh '${base}' HEAD", returnStdout: true)
        writeFile file: 'change.env', text: detected
        detected.split('\n').each { if (it) { def p=it.split('=',2); env[p[0]]=p[1] } }
      } }
    }
    stage('Quality gates') {
      parallel {
        stage('Pipeline safety tests') {
          when { expression { env.CI_CHANGED == 'true' || !env.CHANGE_ID } }
          steps { sh 'jenkins/tests/run.sh' }
        }
        stage('Backend gates') {
          when { expression { env.BACKEND_CHANGED == 'true' || !env.CHANGE_ID } }
          stages {
            stage('Backend dependencies') {
              steps { sh 'python3.12 -m venv .ci-venv && .ci-venv/bin/pip install -r jenkins/requirements-ci.txt' }
            }
            stage('Backend lint') { steps { sh '.ci-venv/bin/ruff check apps/backend' } }
            stage('Backend type check') { steps { sh '.ci-venv/bin/mypy apps/backend' } }
            stage('Backend tests') {
              steps { sh 'mkdir -p reports && .ci-venv/bin/pytest apps/backend/tests --junitxml=reports/backend.xml' }
            }
          }
          post { always { junit allowEmptyResults: true, testResults: 'reports/backend.xml' } }
        }
        stage('Frontend gates') {
          when { expression { env.FRONTEND_CHANGED == 'true' || !env.CHANGE_ID } }
          stages {
            stage('Frontend dependencies') { steps { dir('apps/frontend') { sh 'npm ci' } } }
            stage('Frontend lint') { steps { dir('apps/frontend') { sh 'npm run lint' } } }
            stage('Frontend type check') { steps { dir('apps/frontend') { sh 'npm exec tsc -- --noEmit' } } }
            stage('Frontend build') { steps { dir('apps/frontend') { sh 'npm run build' } } }
          }
        }
        stage('Migration cycle') {
          when { expression { env.MIGRATION_CHANGED == 'true' || !env.CHANGE_ID } }
          steps { sh '''python3.12 -m venv .migration-venv
            .migration-venv/bin/pip install -r jenkins/requirements-ci.txt
            PATH="$WORKSPACE/.migration-venv/bin:$PATH" jenkins/migration-check.sh''' }
        }
        stage('Terraform plan') {
          when { expression { env.IAC_CHANGED == 'true' } }
          steps { withCredentials([aws(credentialsId: 'heritage-terraform-plan-aws')]) { sh '''terraform -chdir=infra fmt -check -recursive
              terraform -chdir=infra init -backend=false
              terraform -chdir=infra validate
              terraform -chdir=infra plan -no-color -out=tfplan
              terraform -chdir=infra show -json tfplan > terraform-plan.raw.json
              python3 jenkins/redact-terraform-plan.py infra/terraform-plan.raw.json infra/terraform-plan.json
              rm -f infra/terraform-plan.raw.json infra/tfplan
              jenkins/check-artifact-secrets.sh infra/terraform-plan.json''' } }
          post { success { archiveArtifacts artifacts: 'infra/terraform-plan.json', fingerprint: true } }
        }
      }
    }
    stage('Release guard') { when { branch 'main' }; steps { sh 'jenkins/guard-release.sh deploy' } }
    stage('Prepare release corpus') {
      when { branch 'main' }
      steps { withCredentials([aws(credentialsId: 'heritage-staging-aws')]) { sh '''test -n "$CORPUS_S3_URI"
        aws s3 sync --delete "$CORPUS_S3_URI" corpus/
        test -s corpus/locations_index.json
        test -n "$(find corpus/wiki_by_location -type f -name '*.txt' -print -quit)"
        find corpus -type f -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256 | cut -d " " -f 1 > corpus.sha256''' } }
    }
    stage('Build and push immutable images') {
      when { branch 'main' }
      steps { withCredentials([aws(credentialsId: 'heritage-staging-aws')]) { sh 'jenkins/ecr-build-push.sh' } }
      post { success { archiveArtifacts artifacts: 'release-images.env', fingerprint: true } }
    }
    stage('Deploy staging') {
      when { branch 'main' }
      steps { withCredentials([aws(credentialsId: 'heritage-staging-aws')]) { sh 'jenkins/deploy-with-rollback.sh' } }
    }
    stage('Smoke and rollback') {
      when { branch 'main' }
      steps { withCredentials([aws(credentialsId: 'heritage-staging-aws')]) { sh 'jenkins/smoke-and-rollback.sh' } }
    }
  }
  post { always { cleanWs(deleteDirs: true, disableDeferredWipeout: true) } }
}
