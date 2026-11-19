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

References used for setup: [OpenSearch Windows installation, version 3.3](https://docs.opensearch.org/3.3/install-and-configure/install-opensearch/windows/), [Sentence Transformers installation](https://sbert.net/docs/installation.html), [Hugging Face pinned-revision downloads](https://huggingface.co/docs/huggingface_hub/en/guides/download). These document installation interfaces; actual verification results will be recorded separately.
