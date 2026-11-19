# RAG test runtime setup

2026-11-19 (Asia/Saigon). The user explicitly authorized installing missing components and continuing the RAG checks. This supersedes the earlier installation blocker.

Installed in the existing workspace virtual environment, without changing dependency pins:

- PyTorch `2.9.1+cpu`, matching the CPU version already pinned in the backend Dockerfile.
- sentence-transformers `6.1.0`, matching the existing backend manifests.
- Resolved dependencies include transformers `5.23.0` and huggingface-hub `1.33.0`.
- Actual imports and a CPU tensor operation succeeded; `python -m pip check` reports no broken requirements.

OpenSearch `3.3.0` was downloaded from its official release artifact URL and verified against the official SHA512 checksum. The native Windows distribution includes its own JDK and Faiss library. It is configured only for this test cluster at `127.0.0.1:19200` (transport 19300), single node, 512 MiB heap; no Windows service or application `.env` was changed. Windows requires a space-free launch path, so its verified Windows short path is used for the workspace installation. The bundled JDK 24 failed on Windows temporary socket deletion permissions, including with a dedicated temp directory. Using the already installed Temurin Java 21.0.6 resolved startup without changing OpenSearch or weakening its Java policy. HTTP returned 200 and version 3.3.0. The upstream [Windows socket-policy issue](https://github.com/opensearch-project/OpenSearch/issues/20463) explains the same failure class; it is supporting context rather than a claim about a particular fixed release.

Artifacts and model cache are outside the Git repository at `C:\Capstone 1\.rag-test-runtime`. The exact pinned BGE-M3 revision `5617a9f61b028005a4858fdac845db406aefb181` was verified against the Hugging Face model metadata and downloaded. Actual offline CPU inference returned one finite 1024-dimensional vector with norm 1.0. No alternate model/embedding strategy is introduced.

The application's local knowledge metadata has no registered source, and bounded read-only inspection of the configured R2 knowledge prefix found no TXT/MD/HTML/PDF document. With execution approval, an owned 1120-byte temporary smoke-test document was created under `sprint4-tests/<uuid>/` with a unique owner marker and conditional create. Its key/ETag/owner record stays outside the repository. Only that exact owned object will be removed after the tests; no existing object, application database or index is changed.

## Final runtime verification

The Windows launcher also needs the shipped k-NN DLL directory in its process PATH and `java.library.path`. The official root Windows installer sets PATH, while directly invoking `bin/opensearch.bat` does not. Adding the native library path fixed the Faiss load failure without changing the retrieval engine. The owned test cluster's percentage disk watermark initially blocked index creation on this nearly full drive. Test-only absolute thresholds (low 3 GiB, high 2 GiB, flood 1 GiB) were configured after checking more than 4 GiB was free. No application/production cluster setting was changed.

Successful commands and results:

```powershell
$env:OPENSEARCH_TEST_URL='http://127.0.0.1:19200'
& 'C:\Capstone 1\.venv\Scripts\python.exe' -X utf8 -m pytest apps/backend/tests/test_rag_pipeline_schema.py apps/backend/tests/test_rag_pipeline_api.py apps/backend/tests/test_reindex_worker.py apps/backend/tests/test_document_text.py apps/backend/tests/test_reindex_storage.py apps/backend/tests/test_rag_verifier.py apps/backend/tests/test_r2_ingestion.py apps/backend/tests/test_opensearch.py -q --tb=short
```

**49 passed, 24 subtests passed, no skips, one existing warning, 28.89s.** This includes all six actual OpenSearch integration cases. The search file also passed separately: **11 passed in 16.08s**; those overlap the 49 and are not additional cases. Earlier failed attempts exposed the test-runtime disk threshold and missing DLL path, which were fixed before the successful runs.

```powershell
$env:HF_HUB_CACHE='C:\Capstone 1\.rag-test-runtime\hf-hub'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:EMBEDDING_DEVICE='cpu'
$env:OMP_NUM_THREADS='4'
$env:MKL_NUM_THREADS='4'
$env:OPENSEARCH_TEST_URL='http://127.0.0.1:19200'
& 'C:\Capstone 1\.venv\Scripts\python.exe' -X utf8 scripts/sprint4/verify_rag_postgres.py --local-runtime
```

**6 passed, no skips, one existing warning, 60.15s.** Five are actual PostgreSQL migration/queue/concurrency cases; the additional case exercises admin login -> pipeline creation -> job trigger -> worker -> real BGE-M3 -> real OpenSearch -> persisted COMPLETED/counts and a real indexed 1024-dimensional vector. Only the S3 HEAD/GET responses are protocol fixtures; this mode makes no cloud call. The first local-mode attempt inherited the disabled cloud gate and skipped that case; its selector was corrected and a guard test added before the passing six-case run.

The separate `--live` command with actual R2 access was **not executed**: execution approval returned `Rejected("rejected by user")`, with no further reason. It was not resubmitted or relabeled as a passing cloud test. The local-runtime mode is explicit about its S3 fixture and does not bypass that refusal.

Cleanup completed: the exact owned R2 object was checked for matching owner marker/ETag, conditionally deleted, and HEAD returned 404. One index left by an earlier native-library failure was removed only from the verified owned test cluster. Test database schemas/databases, indices and pipelines were removed. The test OpenSearch process was stopped and port 19200 verified closed. Installed packages, archive, model cache and runtime remain available; no worker is left running. The full cloud assertion remains unverified, so BE-06 retains PARTIAL verification.

## Restart the installed local test search

These commands are specific to this Windows workspace and do not register a service or start Docker:

```powershell
$ragSearchHome=Get-Content -LiteralPath 'C:\Capstone 1\.rag-test-runtime\opensearch-short-path.txt' -Raw
$env:OPENSEARCH_JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.6.7-hotspot'
$env:OPENSEARCH_TMPDIR='C:\CAPSTO~1\RAG-TE~1\tmp'
$env:TEMP=$env:OPENSEARCH_TMPDIR
$env:TMP=$env:OPENSEARCH_TMPDIR
$env:PATH="$ragSearchHome\plugins\opensearch-knn\lib;$env:PATH"
$env:OPENSEARCH_JAVA_OPTS="-Xms512m -Xmx512m -XX:ActiveProcessorCount=4 -Djava.library.path=$ragSearchHome\plugins\opensearch-knn\lib"
& "$ragSearchHome\bin\opensearch.bat" -s
```

Run the verification command from another terminal. Temporary cloud source keys from this run were removed after cleanup; a future authorized cloud test needs a fresh owned source or an explicitly configured existing test document.

References used for setup: [OpenSearch Windows installation, version 3.3](https://docs.opensearch.org/3.3/install-and-configure/install-opensearch/windows/), [Sentence Transformers installation](https://sbert.net/docs/installation.html), [Hugging Face pinned-revision downloads](https://huggingface.co/docs/huggingface_hub/en/guides/download). These document installation interfaces; actual verification results will be recorded separately.
