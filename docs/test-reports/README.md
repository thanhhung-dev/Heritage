# Chat Backend FUT

[Download the English workbook](Chat_Backend_Conversation_Management_FUT.xlsx).

The seven-column sheet follows the supplied Login template: module, tester,
precondition, Pass/Fail/total counts, ID, description, procedure, expected result,
actual result, result and test date. It contains **30 functional cases: 30 Pass,
0 Fail, 0 Not Run**, dated **November 7, 2026**.

These are observed automated results, not assumed manual passes. The evidence tab
links each case to the test method/class that actually executed, with durations.
The 19 persistence cases require successful execution on both router paths;
the workbook contains **49 execution links** in total. The complete targeted
backend run passed 91 tests and 85 subtests; a FUT row can summarize several
assertions, so the counts intentionally differ. Tests use controlled AI IO and
isolated SQLite. Real Postgres/HTTP and browser checks are documented separately
in the [task audit](../../apps/backend/CHAT_TASK_AUDIT.md).

Regenerate from repository root using the existing environment with openpyxl:

```powershell
& "C:\Capstone 1\.venv\Scripts\python.exe" -X utf8 -m pytest `
  apps/backend/tests/test_chat_fallback.py `
  apps/backend/tests/test_chat_conversation.py `
  apps/backend/tests/test_chat_api.py `
  apps/backend/tests/test_tour_scope.py `
  apps/backend/tests/test_chat_graphrag.py -q --tb=short `
  --junitxml="$env:TEMP/heritage-chat-junit.xml"

& "C:\Capstone 1\.venv\Scripts\python.exe" -X utf8 scripts/generate-chat-fut.py `
  --junit "$env:TEMP/heritage-chat-junit.xml" --date 2026-11-07 `
  --output docs/test-reports/Chat_Backend_Conversation_Management_FUT.xlsx
```

Use the actual validation date on subsequent runs. The reporting script never
converts missing/skipped evidence into Pass: it writes Not Run; a failed execution
writes Fail. It exits nonzero if any mapped case is not Pass. Summary counts are
generated from those observed results. No reporting dependency was installed or
added to the application runtime.
