pipeline {
  agent { label 'heritage-linux' }
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
          def previous = env.GIT_PREVIOUS_COMMIT ?: ''
          withEnv(["CANDIDATE_BASE=${previous}"]) {
            base = sh(script: 'if test -n "$CANDIDATE_BASE" && git cat-file -e "$CANDIDATE_BASE^{commit}" 2>/dev/null; then printf "%s" "$CANDIDATE_BASE"; else git rev-parse HEAD~1 2>/dev/null || git hash-object -t tree /dev/null; fi', returnStdout: true).trim()
          }
        }
        sh "jenkins/change-detection.sh '${base}' HEAD"
        sh 'python3 jenkins/python/release_plan.py'
        readFile('.ci-components.env').split('\n').each { if (it) { def p=it.split('=',2); env[p[0]]=p[1] } }
        readFile('.ci-release.env').split('\n').each { if (it) { def p=it.split('=',2); env[p[0]]=p[1] } }
      } }
    }
    stage('Quality gates') {
      parallel {
        stage('Pipeline safety tests') {
          when { expression { env.CI_PROFILE_CONTRACTS == 'true' } }
          steps { sh 'jenkins/tests/run.sh' }
        }
        stage('Backend gates') {
          when { expression { env.CI_PROFILE_BACKEND == 'true' } }
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
          when { expression { env.CI_PROFILE_FRONTEND == 'true' } }
          stages {
            stage('Frontend dependencies') { steps { dir('apps/frontend') { sh 'npm ci' } } }
            stage('Frontend lint') { steps { dir('apps/frontend') { sh 'npm run lint' } } }
            stage('Frontend type check') { steps { dir('apps/frontend') { sh 'npm exec tsc -- --noEmit' } } }
            stage('Frontend build') { steps { dir('apps/frontend') { sh 'npm run build' } } }
          }
        }
        stage('Migration cycle') {
          when { expression { env.CI_PROFILE_MIGRATION == 'true' } }
          steps { sh '''python3.12 -m venv .migration-venv
            .migration-venv/bin/pip install -r jenkins/requirements-ci.txt
            PATH="$WORKSPACE/.migration-venv/bin:$PATH" jenkins/migration-check.sh''' }
        }
        stage('Terraform plan') {
          when { expression { env.CI_PROFILE_INFRASTRUCTURE == 'true' } }
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
        stage('Data pipeline contracts') {
          when { expression { env.CI_PROFILE_DATA_PIPELINE == 'true' } }
          steps { sh 'python3 -m compileall -q pipelines/ingestion pipelines/graph && test -d graphrag && test -d data' }
        }
        stage('Model/prompt contracts') {
          when { expression { env.CI_PROFILE_MODEL_CONTRACT == 'true' } }
          steps { sh 'python3 -m compileall -q pipelines/training pipelines/evaluation && test -s b_rank_dump.txt' }
        }
      }
    }
    stage('Release guard') { when { allOf { branch 'main'; expression { env.HAS_RELEASE == 'true' } } }; steps { sh 'jenkins/guard-release.sh deploy' } }
    stage('Prepare release corpus') {
      when { allOf { branch 'main'; expression { env.RELEASE_IMAGES?.split(',')?.contains('backend') } } }
      steps { withCredentials([aws(credentialsId: 'heritage-staging-aws')]) { sh '''test -n "$CORPUS_S3_URI"
        aws s3 sync --delete "$CORPUS_S3_URI" corpus/
        test -s corpus/locations_index.json
        test -n "$(find corpus/wiki_by_location -type f -name '*.txt' -print -quit)"
        find corpus -type f -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256 | cut -d " " -f 1 > corpus.sha256''' } }
    }
    stage('Build and push immutable images') {
      when { allOf { branch 'main'; expression { env.HAS_RELEASE == 'true' } } }
      steps { withCredentials([aws(credentialsId: 'heritage-staging-aws')]) { sh 'jenkins/ecr-build-push.sh' } }
      post { success { archiveArtifacts artifacts: 'release-images.env', fingerprint: true } }
    }
    stage('Deploy staging') {
      when { allOf { branch 'main'; expression { env.HAS_RELEASE == 'true' } } }
      steps { withCredentials([aws(credentialsId: 'heritage-staging-aws')]) { sh 'jenkins/deploy-with-rollback.sh' } }
    }
    stage('Smoke and rollback') {
      when { allOf { branch 'main'; expression { env.HAS_RELEASE == 'true' } } }
      steps { withCredentials([aws(credentialsId: 'heritage-staging-aws')]) { sh 'jenkins/smoke-and-rollback.sh' } }
    }
  }
  post { always { cleanWs(deleteDirs: true, disableDeferredWipeout: true) } }
}
