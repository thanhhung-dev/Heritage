"""Build the English chat FUT workbook from observed pytest JUnit results.

Uses the locally available openpyxl reporting tool; no application dependency.
Missing or skipped evidence is Not Run. Failures are never converted to Pass.
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation


# ID, method, description, procedure, expected result, observed assertion summary.
CASES = [
    ("CH-01", "test_atomic_pair_and_citations_are_restored_after_new_http_client",
     "Persist an owned chat and restore complete history",
     "1. Send an authenticated grounded question.\n2. Open a new HTTP client.\n3. Read the conversation history and compare citations.",
     "HTTP 201 with conversation/message UUIDs; both turns and normalized citations persist and restore unchanged.",
     "Both turns, response metadata and citation records were committed and restored by a new client."),
    ("CH-02", "test_list_and_all_id_access_enforce_account_isolation_before_ai",
     "Isolate account lists, history, append and delete",
     "1. Create conversations for A and B.\n2. List as A.\n3. Attempt to read, append to and delete A's UUID as B.",
     "Each list contains only its owner; cross-account operations return 403 before inference.",
     "Lists excluded other owners; cross-account read, append and delete were rejected with 403."),
    ("CH-03", "test_saved_history_reaches_generation_and_cannot_be_replaced_by_client",
     "Use server-owned history for continued chat",
     "1. Create an owned conversation.\n2. Append using its UUID.\n3. Try replacing context with client-supplied history.",
     "Saved history reaches generation; replacement client history returns 400.",
     "Continuation used stored turns; replacement history was rejected."),
    ("CH-04", "test_owner_delete_cascades_and_leaves_other_account_intact",
     "Delete an owned conversation and cascade its records",
     "1. Create A and B conversations with citations.\n2. Delete A's conversation as A.\n3. Inspect child rows and B's history.",
     "HTTP 204; A's conversation, messages and citations disappear; B remains unchanged.",
     "Owner deletion cascaded through child records while preserving the other account's history."),
    ("CH-05", "test_guest_uuid_never_grants_read_resume_or_account_claim",
     "Define safe Guest behavior without UUID-based access",
     "1. Send a message without Authorization.\n2. Try resuming/reading the Guest UUID.\n3. Try claiming it after login.",
     "New Guest chat returns 201 with null owner; no read, resume or account claim is granted by its UUID.",
     "Guest creation succeeded; UUID-based access and later account claiming were denied."),
    ("CH-06", "test_invalid_expired_wrong_purpose_headers_are_not_treated_as_guests",
     "Reject invalid authentication instead of downgrading to Guest",
     "1. Send malformed and invalid bearer headers.\n2. Send expired and wrong-purpose JWTs.\n3. Inspect response and persistence.",
     "Invalid supplied authentication returns 401 and creates no Guest conversation.",
     "Malformed, invalid, expired and wrong-purpose credentials were rejected; no Guest downgrade occurred."),
    ("CH-07", "test_inactive_or_deleted_account_cannot_chat",
     "Reject disabled or deleted account identities",
     "1. Issue an account JWT.\n2. Disable or delete the account in the isolated database.\n3. Send a chat request.",
     "HTTP 401; an otherwise signed JWT cannot bypass the active-account check.",
     "Disabled/deleted accounts were rejected without saving a chat."),
    ("CH-08", "test_clarification_and_abstention_restore_their_complete_outcome",
     "Preserve clarification and abstention contracts in history",
     "1. Trigger clarification and insufficient-evidence outcomes.\n2. Read stored history.\n3. Compare outcome fields and citations.",
     "Choice/question/abstention fields survive restoration without fabricated citations.",
     "The persisted outcomes retained their clarification and abstention metadata."),
    ("CH-09", "test_social_response_can_persist_without_fabricated_citations",
     "Allow social conversation without invented sources",
     "1. Submit a greeting.\n2. Persist a conversation-type answer.\n3. Inspect sources and child citation rows.",
     "HTTP 201; the social reply has no historical citations and passes the database answer gate.",
     "A social reply persisted successfully without fabricated citations."),
    ("CH-10", "test_model_clarification_is_exposed_and_restored_without_citations",
     "Expose a safe model clarification question",
     "1. Return a clarification from controlled generation.\n2. Inspect the immediate reply.\n3. Restore history.",
     "needs_user_choice is true; a safe clarification_question is exposed/restored with empty citations.",
     "Model clarification was normalized and restored without unsupported evidence."),
    ("CH-11", "test_guest_context_and_provider_http_contract_are_connected",
     "Connect bounded context to the existing provider HTTP contract",
     "1. Send a Guest question with context hints and bounded history.\n2. Capture controlled provider HTTP.\n3. Inspect response and citations.",
     "The current question/history/context reach generation through the existing provider contract.",
     "Controlled provider HTTP received the expected question and bounded contextual data."),
    ("CH-12", "test_multiple_source_order_and_bounded_server_history_survive_restoration",
     "Bound server context and retain citation ordering",
     "1. Save multiple turns and sources.\n2. Continue the conversation.\n3. Inspect model context and restored source order.",
     "At most six messages, 2,000 characters per message and 6,000 total; source order remains stable.",
     "Server context obeyed its bounds; multiple citations restored in original order."),
    ("CH-13", "test_sources_strip_unsafe_urls_and_nonfinite_scores_before_serialization",
     "Sanitize source URLs and scores before persistence",
     "1. Supply sources with unsafe URLs or invalid numeric scores.\n2. Send and restore a chat.\n3. Inspect serialized sources/citations.",
     "Unsafe URLs and nonfinite scores are removed before JSON serialization and storage.",
     "Unsafe source URL values and nonfinite scores were sanitized."),
    ("CH-14", "test_scope_is_inherited_on_resume_and_cannot_be_switched_or_dropped",
     "Keep the conversation locked to its original tour area",
     "1. Create a scoped conversation.\n2. Resume without resending area.\n3. Attempt switching to another area or adding a scope to an unscoped conversation.",
     "Saved area is inherited; inconsistent area changes return 400.",
     "Continuation inherited its server-owned area and refused scope changes."),
    ("CH-15", "test_timeout_does_not_leave_partial_new_or_existing_turns",
     "Roll back inference timeout and ignore late completion",
     "1. Delay inference past the configured test budget.\n2. Try new and existing conversations.\n3. Inspect rows after late completion.",
     "HTTP 504 with safe detail; neither partial turns nor late assistant messages are stored.",
     "Timeout returned 504 and left new/existing conversation rows unchanged."),
    ("CH-16", "test_inference_and_commit_failures_roll_back_every_row",
     "Roll back provider and database commit failures",
     "1. Inject a generation failure.\n2. Inject a commit failure after flush.\n3. Compare conversation/message/citation counts.",
     "HTTP 500 with safe detail; user, assistant and citations remain atomic.",
     "Provider and commit failures returned safe errors and rolled back every partial row."),
    ("CH-17", "test_database_gate_rejects_uncited_answers_and_messages_without_parent",
     "Enforce database grounding and parent constraints",
     "1. Attempt to save an uncited factual answer.\n2. Attempt a message without a valid parent.\n3. Inspect constraint results.",
     "Database constraints reject invalid factual answers and orphan messages.",
     "Answer-gate and parent constraints rejected invalid records."),
    ("CH-18", "test_spoofed_identity_bad_context_and_pagination_are_rejected",
     "Validate identity fields, message/context bounds and pagination",
     "1. Send a spoofed account field and malformed payloads.\n2. Exceed context bounds.\n3. Send invalid pagination values.",
     "HTTP 422; invalid bodies/pagination cannot reach inference or persistence.",
     "Spoofed identity, invalid context and invalid pagination were rejected."),
    ("CH-19", "test_draft_missing_heritage_and_unknown_conversation_are_rejected",
     "Reject unpublished/missing heritage and unknown conversations",
     "1. Reference a draft or missing heritage.\n2. Reference an unknown conversation UUID.\n3. Inspect errors and persisted rows.",
     "HTTP 404 for unavailable records; no invalid conversation is saved.",
     "Draft/missing heritage and unknown conversation references were rejected."),
    ("CH-20", "test_local_missing_model_persists_labelled_mock_with_original_sources",
     "Keep local standalone chat usable when the model is absent",
     "1. Enable local fallback without an AI key.\n2. Fail model generation.\n3. Inspect stored reply and original sources.",
     "HTTP 201 with a clearly labeled Development mock and preserved original sources.",
     "Missing-model fallback saved a labeled Development reply and its source records."),
    ("CH-21", "test_local_scoped_outage_abstains_without_gemini_or_foreign_sample_sources",
     "Keep local fallback inside the tour scope",
     "1. Enable local fallback for a locked tour.\n2. Fail generation.\n3. Inspect outcome and general fallback calls.",
     "HTTP 201, abstained=true, service_unavailable, no demo/foreign citations; general Gemini fallback is not called.",
     "The scoped outage abstained with no citations and did not invoke the general fallback."),
    ("CH-22", "test_local_short_inference_timeout_never_appends_a_late_answer",
     "Bound local fallback latency and prevent late duplicates",
     "1. Delay local primary inference.\n2. Let the shorter local budget expire.\n3. Wait for the original worker to finish.",
     "Only one fallback response pair is saved; late generation cannot append another answer.",
     "Only the committed fallback pair existed after the late worker completed."),
    ("CH-23", "test_development_fallback_can_be_disabled_and_is_never_used_in_production",
     "Disable Development fallback in strict and production modes",
     "1. Fail generation in production with the flag enabled.\n2. Fail it locally with fallback disabled.\n3. Inspect results and row counts.",
     "Both cases fail safely with HTTP 500 and no persisted partial conversation.",
     "Production and explicit opt-out did not use Development fallback."),
    ("CH-24", "test_gemini_http_contract_uses_key_header_and_rejects_incomplete_output",
     "Validate optional Gemini fallback HTTP and completion checks",
     "1. Intercept controlled Gemini HTTP.\n2. Verify key header, evidence and history.\n3. Return an incomplete finish reason.",
     "Key is carried in the header; incomplete answers are rejected; no real credentials/network are used.",
     "Gemini request shape and history were verified; incomplete output was rejected."),
    ("CH-25", "test_no_key_returns_labelled_fixture_with_no_fabricated_source_url",
     "Label demo fallback and avoid fabricated historical URLs",
     "1. Enable local fallback without a key or evidence.\n2. Generate the fallback.\n3. Inspect answer label and source URL.",
     "Development mock is explicitly labeled; demo source has no fabricated public URL.",
     "The fallback clearly identified demo data and did not invent a public source URL."),
    ("CH-26", "test_foreign_question_comparison_and_injection_never_retrieve",
     "Decline foreign-area questions before retrieval",
     "1. Lock chat to the current area.\n2. Ask about another site, a cross-site comparison and scope-changing instructions.\n3. Inspect retrieval calls.",
     "A scope notice is returned; foreign-area questions never trigger retrieval or change the tour.",
     "Foreign questions, comparisons and injection attempts were blocked before retrieval."),
    ("CH-27", "test_broader_subject_gets_a_friendly_notice_without_changing_tour",
     "Explain the current scope for a broader regional topic",
     "1. Open a locked heritage tour.\n2. Ask about a broader regional topic.\n3. Inspect reply, sources and active area.",
     "A friendly current-area notice is shown without navigation or unrelated sources.",
     "The broader-topic reply kept the current tour and used a friendly scope notice."),
    ("CH-28", "test_locked_provider_receives_policy_history_and_scene_as_data",
     "Separate trusted area policy from story and conversation hints",
     "1. Send a locked request with history and a scene title.\n2. Capture generation input.\n3. Inspect trusted policy versus user data.",
     "Server policy remains separate; scene/history are bounded contextual data, never source evidence.",
     "The provider received the server area policy separately from scene/history data."),
    ("CH-29", "test_graph_failure_preserves_hybrid_evidence",
     "Retain Hybrid RAG when optional GraphRAG fails",
     "1. Supply valid Hybrid evidence.\n2. Fail optional GraphRAG.\n3. Inspect the evidence passed to generation.",
     "Graph failure does not discard valid Hybrid evidence or introduce graph-generated claims as sources.",
     "Valid Hybrid evidence remained usable after optional graph failure."),
    ("CH-30", "test_stale_mapping_or_incomplete_lineage_never_reaches_prompt",
     "Reject graph evidence without valid passage lineage",
     "1. Supply stale graph mappings or incomplete lineage.\n2. Build the generation context.\n3. Inspect prompt evidence.",
     "Unsupported graph context cannot reach the prompt or become a citation.",
     "Stale or incomplete graph evidence was excluded from the generation prompt."),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", required=True, type=Path)
    parser.add_argument("--date", required=True, type=date.fromisoformat)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = ElementTree.parse(args.junit).getroot()
    executions = list(root.iter("testcase"))
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Chat Backend FUT"
    title = "Complete the Chat Backend and Account-Based Conversation Management"
    precondition = (
        "Automated checks: isolated SQLite, real ORM/JWT handling, controlled retrieval and provider HTTP responses. "
        "Fault tests disable local fallback unless fallback itself is under test. "
        "Pass means observed assertions passed; real-model historical accuracy is evaluated separately."
    )
    for row, label, value in ((1, "Module Code", title), (2, "Tester", "Cao Van Khoa"), (3, "Pre-condition", precondition)):
        sheet.cell(row, 1, label)
        sheet.merge_cells(start_row=row, start_column=2, end_row=row, end_column=7)
        sheet.cell(row, 2, value)
    sheet.cell(4, 1, "Pass")
    sheet.cell(4, 2, "Fail")
    sheet.merge_cells("C4:G4")
    sheet.cell(4, 3, "Number of test case")
    sheet.merge_cells("C5:G5")
    sheet.append([])
    for column, value in enumerate(("ID", "Test case Description", "Test case Procedure", "Expected Result", "Actual Result", "Result", "Test Date"), 1):
        sheet.cell(7, column, value)
    sheet.merge_cells("A8:G8")
    sheet.cell(8, 1, title)
    evidence = workbook.create_sheet("Automated Evidence")
    evidence.append(["FUT ID", "Automated test", "Class", "Observed result", "Duration (seconds)"])
    statuses = []
    for case in CASES:
        case_id, method, description, procedure, expected, observed = case
        matches = [execution for execution in executions if execution.get("name") == method]
        # Every persistence scenario must execute on BOTH mounted router paths.
        required_classes = ({"ChatConversationTests", "RefactoredChatConversationTests"}
                            if int(case_id.removeprefix("CH-")) <= 19 else set())
        observed_classes = {execution.get("classname", "").split(".")[-1] for execution in matches}
        failed = any(execution.find("failure") is not None or execution.find("error") is not None for execution in matches)
        skipped = any(execution.find("skipped") is not None for execution in matches)
        status = "Fail" if failed else "Not Run" if not matches or skipped or not required_classes <= observed_classes else "Pass"
        statuses.append(status)
        actual = (observed if status == "Pass" else "Observed automated failure; inspect evidence." if failed
                  else "Required automated execution was absent or skipped.")
        sheet.append([case_id, description, procedure, expected, actual, status, args.date])
        for execution in matches:
            result = "Fail" if execution.find("failure") is not None or execution.find("error") is not None else "Not Run" if execution.find("skipped") is not None else "Pass"
            evidence.append([case_id, method, execution.get("classname"), result, float(execution.get("time", "0"))])
    sheet.cell(5, 1, statuses.count("Pass"))
    sheet.cell(5, 2, statuses.count("Fail"))
    sheet.cell(5, 3, len(CASES))
    sheet.freeze_panes = "D9"
    sheet.auto_filter.ref = f"A7:G{sheet.max_row}"
    sheet.sheet_view.showGridLines = False
    thin = Side(style="thin", color="555555")
    for row in sheet:
        for cell in row:
            cell.font = Font(name="Times New Roman", size=13, bold=cell.row in {1, 2, 4, 7} or cell.column == 1)
            cell.alignment = Alignment(horizontal="center" if cell.row <= 8 or cell.column in {6, 7} else "left", vertical="center", wrap_text=True)
            cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
    sheet["A8"].font = Font(name="Times New Roman", size=13, bold=True, color="ED7D00")
    for column, width in zip("ABCDEFG", (18, 46, 65, 47, 47, 14, 17)):
        sheet.column_dimensions[column].width = width
    for row_number in range(1, 9):
        sheet.row_dimensions[row_number].height = 52 if row_number == 3 else 28 if row_number == 7 else 23
    for row_number in range(9, sheet.max_row + 1):
        sheet.row_dimensions[row_number].height = 116
        sheet.cell(row_number, 7).number_format = "mm/dd/yyyy"
        cell = sheet.cell(row_number, 6)
        cell.fill = PatternFill("solid", fgColor={"Pass": "E2F0D9", "Fail": "FCE4D6", "Not Run": "FFF2CC"}[cell.value])
        cell.font = Font(name="Times New Roman", size=13, bold=True, color="006100" if cell.value == "Pass" else "9C0006")
    validation = DataValidation(type="list", formula1='"Pass,Fail,Not Run"')
    validation.errorTitle = "Invalid result"
    validation.error = "Choose Pass, Fail or Not Run."
    validation.showErrorMessage = True
    validation.showDropDown = False
    sheet.add_data_validation(validation)
    validation.add(f"F9:F{sheet.max_row}")
    sheet.print_title_rows = "1:8"
    sheet.print_area = f"A1:G{sheet.max_row}"
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A3
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    evidence.freeze_panes = "B2"
    evidence.auto_filter.ref = evidence.dimensions
    for column, width in zip("ABCDE", (14, 96, 78, 18, 22)):
        evidence.column_dimensions[column].width = width
    for row in evidence:
        for cell in row:
            cell.font = Font(name="Times New Roman", size=12, bold=cell.row == 1)
            cell.alignment = Alignment(vertical="center", wrap_text=True)
    workbook.properties.title = title
    workbook.properties.creator = "Cao Van Khoa"
    workbook.properties.description = "English FUT based on observed automated assertions; controlled AI IO."
    args.output.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(args.output)
    print(f"FUT: {len(CASES)} cases, {statuses.count('Pass')} Pass, {statuses.count('Fail')} Fail, {statuses.count('Not Run')} Not Run")
    if any(status != "Pass" for status in statuses):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
