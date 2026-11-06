"""Render the supplied seven-column FUT form; never invent execution results.

Run from the repository root with a Python environment containing openpyxl:
    python generate_feature_fut.py

This reporting utility does not call application APIs, run tests, or write to a
database. The backend cases are a snapshot of the existing Chat Backend FUT
catalogue, with old execution claims removed. All cases start as Not Run.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from textwrap import wrap
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile
from zoneinfo import ZoneInfo

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.workbook.properties import CalcProperties
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.page import PageMargins

ROOT = Path(__file__).resolve().parent
TESTER = "Cao Van Khoa"
HEADERS = ("ID", "Test case Description", "Test case Procedure", "Expected Result",
           "Actual Result", "Result", "Test Date")
WIDTHS = (19, 43, 66, 58, 43, 14, 17)
STATES = {"Pass": ("D9EAD3", "274E13"), "Fail": ("F4CCCC", "990000"),
          "Blocked": ("FCE5CD", "783F04"), "Not Run": ("EEEEEE", "595959")}
THIN = Side(style="thin", color="595959")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def case(case_id, group, description, steps, expected, source):
    return {"id": case_id, "group": group, "description": description,
            "procedure": "\n".join(f"{i}. {step}" for i, step in enumerate(steps, 1)),
            "expected": expected, "source": source}


SEARCH_CASES = [
    case("HS_UI_01", "Page and catalogue", "Load the Search results layout",
         ["Start the frontend and published catalogue API.", "Open /search on a desktop viewport."],
         "The dark photo banner, navigation, search bar, category/location sidebar, result area and recommendation section are visible without a runtime error.",
         "apps/frontend/features/search/HeritageSearchPage.tsx"),
    case("HS_UI_02", "Page and catalogue", "Display real tour metadata and open a tour",
         ["Load a published tour with image, region, description, languages and duration.", "Inspect its horizontal result row and activate its title or image."],
         "The row reflects API metadata and opens /content/{slug}. Missing optional metadata is handled without inventing facts.",
         "apps/frontend/features/search/HeritageResultCard.tsx"),
    case("HS_QRY_01", "Query input", "Debounce text input",
         ["Open /search with a populated catalogue.", "Type several characters less than 400 ms apart.", "Wait at least 400 ms after the last change and inspect the URL and results."],
         "The final trimmed query is written to q after the debounce; intermediate drafts do not replace the final query. The current catalogue is filtered without a new request for each keystroke.",
         "apps/frontend/features/search/useSearchUrl.ts"),
    case("HS_QRY_02", "Query input", "Submit a query immediately with Enter",
         ["Type a known heritage keyword.", "Press Enter before the debounce finishes."],
         "The submitted query updates the URL and results immediately; pagination resets to page 1.",
         "apps/frontend/features/search/useSearchUrl.ts"),
    case("HS_QRY_03", "Query input", "Match case-insensitive and accent-insensitive terms",
         ["Use a published tour titled Lang Tu Duc in Vietnamese with accents.", "Search for LANG tu DUC without accents.", "Search for an additional term absent from that tour."],
         "All matching terms are compared without case/accent sensitivity. Adding a missing term excludes the tour.",
         "apps/frontend/tests/heritage-search.test.ts"),
    case("HS_QRY_04", "Query input", "Handle whitespace and query length boundaries",
         ["Search using surrounding spaces and then whitespace only.", "Enter more than 200 characters, including through a direct q URL."],
         "Surrounding whitespace is trimmed. A blank query removes q. The parsed query is bounded to 200 characters without breaking the page.",
         "apps/frontend/features/search/search-params.ts"),
    case("HS_QRY_05", "Query input", "Wait for IME composition to finish",
         ["Focus the search field and start an IME composition.", "Keep composing for longer than 400 ms and press Enter to confirm composition.", "End composition and wait for debounce."],
         "An unfinished composed query is not submitted. The completed text is applied after composition ends.",
         "apps/frontend/features/search/useSearchUrl.ts"),
    case("HS_FLT_01", "Category and location filters", "Select and deselect a category",
         ["Provide explicit category metadata on published catalogue records.", "Select a category checkbox and inspect the results and URL.", "Deselect the same checkbox."],
         "Only matching tours remain; category is represented in the URL. Deselecting removes that constraint and restores matching tours.",
         "apps/frontend/features/search/SearchFilters.tsx"),
    case("HS_FLT_02", "Category and location filters", "Filter by region and a heritage site",
         ["Select a region containing several published tours.", "Select one site's location checkbox.", "Inspect repeated region/location parameters and displayed rows."],
         "Region and site constraints combine; selected site values use the heritage slug. Counts and labels come from catalogue metadata.",
         "apps/frontend/features/search/SearchFilters.tsx"),
    case("HS_FLT_03", "Category and location filters", "Apply OR within a group and AND between groups",
         ["Select two available regions and two categories.", "Add a query and select one site.", "Compare the results with the fixture catalogue."],
         "A tour may match either selected value within one group, but it must satisfy the query and every active filter group.",
         "apps/frontend/tests/heritage-search.test.ts"),
    case("HS_FLT_04", "Category and location filters", "Keep facet counts available after an empty search",
         ["Record the category and region counts for a populated catalogue.", "Search for a phrase matching no tour."],
         "Counts still describe the full catalogue. Filters remain available so the user can recover from the empty result.",
         "apps/frontend/features/search/catalogue.ts"),
    case("HS_FLT_05", "Category and location filters", "Handle missing categories truthfully",
         ["Provide a published tour without a category field.", "Inspect its category facet and select Uncategorized."],
         "The tour appears under Uncategorized. No category is guessed from its title or description.",
         "apps/frontend/tests/heritage-search.test.ts"),
    case("HS_FLT_06", "Category and location filters", "Recover from unknown filters in a shared URL",
         ["Open /search?region=Unknown&category=Unknown&location=unknown-site.", "Inspect the selected filter controls.", "Deselect the unknown options or use Clear all."],
         "Unknown selected values remain visible and removable even with zero matches. Unselected categories with no catalogue records are disabled.",
         "apps/frontend/features/search/SearchFilters.tsx"),
    case("HS_FLT_07", "Category and location filters", "Preserve rapid checkbox selections",
         ["Toggle several different category/region/site checkboxes rapidly before navigation settles.", "Wait for the URL update."],
         "Every final selection is preserved; rapid changes do not overwrite one another. Results match the final URL state.",
         "apps/frontend/features/search/useSearchUrl.ts"),
    case("HS_URL_01", "URL state and pagination", "Restore query, filters and page from a shared URL",
         ["Open a valid URL with q, repeated region/category/location parameters, page=2 and source=fut.", "Reload the page and inspect controls and rows."],
         "The query, selected checkboxes and valid page are restored. Repeated filter values are supported and unrelated parameters survive.",
         "apps/frontend/tests/heritage-search.test.ts"),
    case("HS_URL_02", "URL state and pagination", "Restore state with browser Back and Forward",
         ["Submit a query, toggle a filter, then navigate to another page of matching results.", "Use browser Back and Forward through those navigation entries."],
         "Input, filter controls, result rows and pagination consistently follow the current URL; stale drafts do not overwrite restored state.",
         "apps/frontend/features/search/useSearchUrl.ts"),
    case("HS_URL_03", "URL state and pagination", "Preserve Unicode and unrelated query parameters",
         ["Open a search URL containing an accented heritage name and source=fut.", "Change filters and navigate to another result page."],
         "Unicode round-trips correctly; source=fut remains present while only owned search parameters are updated.",
         "apps/frontend/tests/heritage-search.test.ts"),
    case("HS_PAG_01", "URL state and pagination", "Paginate a catalogue without gaps or duplicates",
         ["Provide 23 distinct published matching tours.", "Visit every result page and record the displayed slugs."],
         "Pages 1-5 show four tours each; page 6 shows three. The union contains exactly 23 distinct tours with no skipped or duplicated rows.",
         "apps/frontend/tests/heritage-search.test.ts"),
    case("HS_PAG_02", "URL state and pagination", "Reset pagination when search constraints change",
         ["Navigate beyond page 1 with active filters.", "Change the query, category, region and site one at a time."],
         "Each constraint change resets pagination to page 1 while preserving all other applicable constraints.",
         "apps/frontend/tests/heritage-search.test.ts"),
    case("HS_PAG_03", "URL state and pagination", "Normalize invalid and out-of-range pages",
         ["Open URLs with page=0, -1, NaN, 2.4, Infinity and an unsafe integer.", "Open page=999 for a nonempty catalogue with only a few pages."],
         "Invalid page values resolve to page 1. An excessive valid page resolves to the last matching page and the URL is corrected.",
         "apps/frontend/tests/heritage-search.test.ts"),
    case("HS_PAG_04", "URL state and pagination", "Prevent stale pagination during a pending query",
         ["Type a new query while pagination is visible.", "Attempt to navigate before debounce/navigation completes.", "Wait for the new results."],
         "Page controls are temporarily disabled during pending input/navigation and cannot submit the previous query. Clear all remains usable.",
         "apps/frontend/features/search/HeritageSearchPage.tsx"),
    case("HS_URL_04", "URL state and pagination", "Clear all active constraints and pending input",
         ["Set a query, multiple filters and a later result page.", "Start typing another query and immediately activate Clear all."],
         "The field, selected filters and page reset. Pending debounce cannot restore old constraints. Unrelated URL parameters remain intact.",
         "apps/frontend/features/search/useSearchUrl.ts"),
    case("HS_UX_01", "Feedback and resilience", "Display a skeleton while the catalogue is loading",
         ["Delay GET /api/heritages using browser request throttling or interception.", "Open /search and then release a valid response."],
         "Loading placeholders/status are visible until the request completes. The page then displays the catalogue without a blank screen.",
         "apps/frontend/features/search/useHeritageSearch.ts"),
    case("HS_UX_02", "Feedback and resilience", "Display no matches while retaining recommendations",
         ["Load a nonempty catalogue.", "Search for a phrase that matches no tour."],
         "A centered no-results message is shown. Search/filter controls and deduplicated catalogue recommendations remain available.",
         "apps/frontend/features/search/SearchFeedback.tsx"),
    case("HS_UX_03", "Feedback and resilience", "Handle an empty published catalogue",
         ["Return [] from GET /api/heritages.", "Open /search and inspect filters, feedback and recommendations."],
         "The page shows an honest empty state and recommendation placeholder. No fictitious production tours or category counts are substituted.",
         "apps/frontend/features/search/HeritageSearchPage.tsx"),
    case("HS_UX_04", "Feedback and resilience", "Recover from an API error or malformed response",
         ["Return HTTP 503 from GET /api/heritages, then retry with a valid catalogue.", "Repeat with an invalid payload such as {items: []}."],
         "An explicit error and retry action are shown; invalid data is rejected. Retry recovers when the API becomes valid. No silent mock catalogue is injected.",
         "apps/frontend/tests/heritage-search.test.ts"),
    case("HS_UX_05", "Feedback and resilience", "Time out and cancel catalogue requests safely",
         ["Delay the catalogue longer than its 15-second deadline.", "Observe the error, then retry successfully.", "Start another delayed request and leave the page before it completes."],
         "The deadline produces recoverable feedback. Unmounted/cancelled requests do not update a departed page or overwrite newer state.",
         "apps/frontend/features/search/useHeritageSearch.ts"),
    case("HS_IMG_01", "Images and recommendations", "Recover from broken or unsafe images",
         ["Supply a broken HTTP image and an unsafe javascript or protocol-relative image URL.", "Inspect the banner, result rows and recommendation cards."],
         "Broken or rejected images use neutral/dark fallbacks. Unsafe image URLs are not loaded, and the result layout remains usable.",
         "apps/frontend/features/search/catalogue.ts"),
    case("HS_REC_01", "Images and recommendations", "Display up to five distinct recommendations",
         ["Provide at least eight distinct published tours and inspect page 1.", "Inspect recommendation slugs and follow a recommendation link.", "Repeat with fewer than five tours."],
         "Recommendations are deduplicated, capped at five and prefer tours outside the visible page. Links open the correct tour; smaller catalogues do not get invented entries.",
         "apps/frontend/tests/heritage-search.test.ts"),
    case("HS_DATA_01", "Page and catalogue", "Exclude unpublished tours and use the real catalogue contract",
         ["Return published and preview/draft records using the HeritageOut array contract.", "Inspect displayed rows and the requested endpoint."],
         "Only published tours appear. The frontend calls GET /api/heritages and filters/paginates the catalogue locally; it does not require an unavailable server-search endpoint.",
         "apps/frontend/tests/heritage-search.test.ts"),
    case("HS_RWD_01", "Responsive layout and accessibility", "Use Search on narrow mobile screens",
         ["Open /search at 375x812 and 320x568.", "Expand/collapse Filters, toggle a checkbox and scroll recommendations horizontally."],
         "Controls remain usable, selected-count feedback updates and the page has no horizontal overflow. The input uses mobile-safe sizing and checkbox targets are touch friendly.",
         "apps/frontend/features/search/search.module.css"),
    case("HS_A11Y_01", "Responsive layout and accessibility", "Operate search, filters and pagination with the keyboard",
         ["Use Tab, Enter and Space to operate the query, Clear all, filter checkboxes, pagination and a tour link.", "Inspect visible focus and loading/error announcements."],
         "Controls have meaningful labels and visible focus; keyboard operation works. Status changes are announced without trapping focus.",
         "apps/frontend/features/search/SearchFilters.tsx"),
    case("HS_REG_01", "Responsive layout and accessibility", "Keep Search-specific header/footer styles scoped",
         ["Open /search and inspect its reference layout.", "Navigate to the FAQ page and another public page."],
         "Search uses its intended header/footer treatment. Other public pages retain their normal shared shell after navigation.",
         "apps/frontend/features/search/SEARCH_RESULTS_DESIGN.md"),
    case("HS_BUILD_01", "Responsive layout and accessibility", "Build the Search route with its Suspense boundary",
         ["From apps/frontend, run npm run build.", "Start the production build and open /search with query parameters."],
         "The production build completes successfully. Search-parameter components render under the existing Suspense fallback without a prerender error.",
         "apps/frontend/app/(public)/search/page.tsx"),
]


TOUR_CASES = [
    case("TC_MNT_01", "Mount and viewer interaction", "Show Ask AI on a direct scene URL before model readiness",
         ["Open /content/tapestry-test/s0 directly.", "Delay the GLB model request."],
         "Ask AI is visible before the model is ready. The URL remains on /s0 instead of redirecting to the splash page.",
         "apps/frontend/app/(tour)/content/[slug]/layout.tsx"),
    case("TC_MNT_02", "Mount and viewer interaction", "Keep the widget available when model loading fails",
         ["Return an error for the GLB request on a direct scene route.", "Open the chat launcher."],
         "The launcher and chat panel remain available despite the failed model. No model-readiness redirect removes the widget.",
         "apps/frontend/features/chat/CHAT_OVERLAY_MOUNT.md"),
    case("TC_UI_01", "Window and positioning", "Open and close the floating glass chat panel",
         ["Activate Ask AI.", "Inspect the avatar, online indicator, heritage/scene labels, guest/member badge and window controls.", "Close using the close button and reopen."],
         "The glass panel opens/closes smoothly, displays current labels and retains its in-memory messages. Closing returns focus to the launcher.",
         "apps/frontend/features/chat/components/ChatOverlayWidget.tsx"),
    case("TC_UI_02", "Window and positioning", "Expand and restore the chat window",
         ["Open the panel, activate Expand chat and then Restore chat size.", "Repeat near a viewport edge."],
         "The panel changes size without losing the draft/history and remains within viewport bounds.",
         "apps/frontend/features/chat/components/ChatOverlayWidget.tsx"),
    case("TC_DRG_01", "Window and positioning", "Drag the launcher without accidentally opening it",
         ["Press and drag the closed AI launcher to another part of the screen.", "Release it, then click without dragging."],
         "The launcher moves and remains closed after a drag. A normal click still opens the chat near the positioned launcher.",
         "apps/frontend/features/chat/useOverlayDrag.ts"),
    case("TC_DRG_02", "Window and positioning", "Drag the panel by its header without hijacking controls",
         ["Open chat and drag an unused portion of its header.", "Select message text and use the close/expand/reset buttons."],
         "The header moves the window. Interactive controls and message text are not treated as drag handles.",
         "apps/frontend/features/chat/useOverlayDrag.ts"),
    case("TC_DRG_03", "Window and positioning", "Clamp dragging and resizing to the visible viewport",
         ["Drag the launcher and panel beyond each screen edge.", "Resize the browser or change device orientation."],
         "The launcher/window stay reachable inside viewport/safe-area bounds and are reclamped when available space changes.",
         "apps/frontend/features/chat/overlay-position.ts"),
    case("TC_DRG_04", "Window and positioning", "Move the widget using keyboard and touch",
         ["Focus the closed launcher or open header; use arrow keys, then Shift plus an arrow.", "Repeat a drag with a touch pointer on a mobile viewport."],
         "Arrow keys move the focused widget and Shift increases the step. Touch dragging works without leaving the controls offscreen.",
         "apps/frontend/features/chat/useOverlayDrag.ts"),
    case("TC_CAN_01", "Mount and viewer interaction", "Continue rotating and zooming the 3D canvas outside chat",
         ["Open the chat while a model is ready.", "Drag and use the mouse wheel on visible canvas outside the panel."],
         "Canvas pointer/wheel input remains available outside chat. The full-screen dock has pointer-events:none; interactive chat elements have pointer-events:auto.",
         "apps/frontend/features/chat/chat-overlay.module.css"),
    case("TC_CAN_02", "Mount and viewer interaction", "Contain input and scrolling inside the widget",
         ["Focus the chat input and type keys also used by viewer navigation.", "Scroll a long message list inside the panel."],
         "Typing and scrolling operate chat without triggering underlying viewer keyboard/wheel actions.",
         "apps/frontend/features/chat/components/ChatOverlayWidget.tsx"),
    case("TC_SCN_01", "Context and session lifecycle", "Preserve chat while navigating between scenes",
         ["Send a question and type a draft in /content/tapestry-test/s0.", "Navigate to scene s1 within the same heritage."],
         "In-memory messages and draft remain; the current scene label changes to the selected scene.",
         "apps/frontend/features/chat/HeritageChatOverlay.tsx"),
    case("TC_SCN_02", "Context and session lifecycle", "Send a quick suggestion with the current heritage/scene",
         ["Start a new conversation in a scene.", "Activate an overview/history/architecture suggestion.", "Inspect the outgoing question and repeat in a different scene."],
         "Suggestion placeholders are replaced with the current tour/scene names. On this branch the legacy request body is {message, use_rag:true}; it does not send heritage_id or conversation_id.",
         "apps/frontend/features/chat/HeritageChatOverlay.tsx"),
    case("TC_INP_01", "Composer and message stream", "Send with Enter and add a line with Shift+Enter",
         ["Type a nonempty question and press Enter.", "Type another draft and press Shift+Enter."],
         "Enter sends one request; Shift+Enter inserts a newline. Pressing Enter during IME composition does not send an incomplete question.",
         "apps/frontend/features/chat/components/ChatInputBar.tsx"),
    case("TC_INP_02", "Composer and message stream", "Disable empty and duplicate submissions",
         ["Inspect Send with empty and whitespace-only input.", "Send a valid question while the API response is delayed.", "Press Enter or activate Send repeatedly."],
         "Empty input cannot be sent. While a request is in flight, no duplicate request is issued and Send shows a waiting state.",
         "apps/frontend/features/chat/useTapestryChat.ts"),
    case("TC_INP_03", "Composer and message stream", "Bound textarea growth and message length",
         ["Type one through five lines in the input.", "Paste text longer than 8000 characters."],
         "The textarea grows up to four visible lines and then scrolls internally. Input is limited to 8000 characters without covering window controls.",
         "apps/frontend/features/chat/components/ChatInputBar.tsx"),
    case("TC_MSG_01", "Composer and message stream", "Display user/assistant messages and safe Markdown",
         ["Send a question and return a controlled answer with a heading, bold text, lists and HTML/script text.", "Inspect both message types."],
         "User messages align right; assistant messages align left. Supported Markdown is formatted while untrusted HTML/scripts are not executed.",
         "apps/frontend/features/chat/components/ChatMarkdown.tsx"),
    case("TC_MSG_02", "Composer and message stream", "Show typing feedback and scroll to the latest answer",
         ["Create enough turns to require internal scrolling.", "Delay a reply and then return it."],
         "The three-dot typing indicator appears only while waiting. The newest turn is scrolled into view when messages or waiting state change.",
         "apps/frontend/features/chat/components/ChatMessageList.tsx"),
    case("TC_CIT_01", "Citations and answer outcomes", "Open source details from a citation badge",
         ["Return an answer with multiple sources and numeric scores.", "Open and close each citation badge and follow a safe source URL."],
         "Each badge shows the correct source title, optional URL and score. Safe links open separately with noopener/noreferrer; toggling details does not reorder messages.",
         "apps/frontend/features/chat/components/ChatMessageList.tsx"),
    case("TC_CIT_02", "Citations and answer outcomes", "Reject unsafe links and support sources without public URLs",
         ["Return sources with a missing URL, javascript URL, protocol-relative URL and a valid HTTPS URL.", "Inspect each source detail panel."],
         "Unsafe/missing URLs are not clickable; an explanatory source detail remains. A valid safe URL can still be opened.",
         "apps/frontend/lib/safe-source-url.ts"),
    case("TC_OUT_01", "Citations and answer outcomes", "Display clarification choices",
         ["Return needs_user_choice=true with candidate suggestions.", "Select one candidate while no other request is running."],
         "The clarification label and deduplicated suggestion buttons are shown. Selecting a candidate sends its question once.",
         "apps/frontend/services/heritageChatService.ts"),
    case("TC_OUT_02", "Citations and answer outcomes", "Distinguish abstention and development sample answers",
         ["Return an insufficient_evidence response with no sources.", "Then return a labelled development_mock response."],
         "The first answer displays No verified answer and does not invent citations. The mock answer is visibly labelled Sample answer rather than presented as verified evidence.",
         "apps/frontend/features/chat/components/ChatMessageList.tsx"),
    case("TC_API_01", "Transport and authentication", "Use the existing legacy chat API contract",
         ["Send a free-form question and inspect Network.", "Check the endpoint, JSON body and correlation header."],
         "One POST /api/chat carries {message: <typed text>, use_rag:true} and X-Correlation-ID. The free-form question is unchanged; the valid answer/sources response is displayed.",
         "apps/frontend/tests/chat-request.test.mjs"),
    case("TC_API_02", "Transport and authentication", "Normalize API base URLs",
         ["Exercise the existing transport test with an origin URL, an /api/ base and same-origin /api."],
         "The resolved endpoint contains exactly one /api/chat suffix; no /api/api/chat duplication occurs.",
         "apps/frontend/tests/chat-request.test.mjs"),
    case("TC_AUTH_01", "Transport and authentication", "Allow Guest chat without an Authorization header",
         ["Remove the access token and open the widget.", "Send a question and inspect request headers."],
         "The badge shows Guest. The request omits Authorization and can display a valid successful response.",
         "apps/frontend/tests/chat-request.test.mjs"),
    case("TC_AUTH_02", "Transport and authentication", "Attach the current member token",
         ["Sign in using a test account.", "Open the overlay, send a question and inspect request headers."],
         "The member badge is displayed and Authorization is Bearer <current access token>. The token is never added to the URL or message text.",
         "apps/frontend/tests/chat-request.test.mjs"),
    case("TC_AUTH_03", "Context and session lifecycle", "Clear local chat when identity or heritage changes",
         ["Create messages and a draft as account A.", "Log out or switch to account B, then open the widget.", "Repeat when switching to a different heritage."],
         "A fresh in-memory session is shown. The previous account/heritage messages and draft are not exposed in the new session.",
         "apps/frontend/features/chat/HeritageChatOverlay.tsx"),
    case("TC_ERR_01", "Errors and cancellation", "Recover from server/network failures without losing the draft",
         ["Return HTTP 503 or simulate a failed network request.", "Inspect the error and input, then resend after the API recovers."],
         "A readable inline error is shown. The failed user turn is removed, the question is restored unless a newer draft exists, and retry can succeed.",
         "apps/frontend/features/chat/useTapestryChat.ts"),
    case("TC_ERR_02", "Errors and cancellation", "Handle HTTP 401 and 403 safely",
         ["Send with an invalid/expired token and return HTTP 401 or 403 with a safe detail.", "Inspect the resulting error."],
         "The authorization error is shown as an error, never as an AI answer. The request is not silently retried as Guest.",
         "apps/frontend/services/heritageChatService.ts"),
    case("TC_ERR_03", "Errors and cancellation", "Reject malformed successful response bodies",
         ["Return HTTP 200 with {answer:123} or invalid JSON.", "Inspect the message list and error state."],
         "Response validation rejects the payload, shows a recoverable format error and restores the draft. No malformed assistant message is appended.",
         "apps/frontend/services/heritageChatService.ts"),
    case("TC_ERR_04", "Errors and cancellation", "Time out an unresponsive chat request",
         ["Delay a chat response beyond the widget's 35-second deadline.", "Observe the error, waiting state and draft.", "Return a late answer and then retry with a healthy response."],
         "Waiting ends with a timeout message and recoverable draft. A late cancelled answer cannot enter the conversation; a new request can succeed.",
         "apps/frontend/features/chat/useTapestryChat.ts"),
    case("TC_ERR_05", "Errors and cancellation", "Reset while inference is pending",
         ["Send a question and delay its reply.", "Activate Start a new conversation, then release the old reply."],
         "The active request is cancelled. Only the welcome message remains, and the late answer cannot repopulate the reset conversation.",
         "apps/frontend/features/chat/useTapestryChat.ts"),
    case("TC_ERR_06", "Errors and cancellation", "Cancel requests when leaving the tour",
         ["Start a delayed chat request.", "Navigate away from the content layout and then release the response."],
         "Unmount aborts the request and clears its timer. No stale response or runtime error affects the next page/session.",
         "apps/frontend/features/chat/useTapestryChat.ts"),
    case("TC_NET_01", "Errors and cancellation", "Update the online/offline indicator",
         ["Open the widget while online.", "Toggle the browser offline and online again."],
         "The status indicator reflects navigator.onLine changes. Failed sends still show actionable errors rather than a fake successful reply.",
         "apps/frontend/features/chat/components/ChatOverlayWidget.tsx"),
    case("TC_MEM_01", "Context and session lifecycle", "Define the current in-memory conversation boundary",
         ["Send several turns, close/reopen the panel and change scenes within the same heritage.", "Reload the browser page."],
         "Messages survive close/reopen and scene changes in the mounted layout. Reload starts a new local session on this branch; persisted conversation listing/history is not claimed by this legacy adapter.",
         "apps/frontend/features/chat/CHAT_OVERLAY_MOUNT.md"),
    case("TC_RWD_01", "Responsive layout and accessibility", "Fit the panel on narrow mobile screens",
         ["Open the widget at 375x812 and 320x568.", "Expand/restore, drag the panel, type a multiline draft and rotate the viewport."],
         "The panel and its controls remain reachable; content scrolls internally without forcing page-wide overflow.",
         "apps/frontend/features/chat/chat-overlay.module.css"),
    case("TC_FS_01", "Mount and viewer interaction", "Keep chat usable in actual browser fullscreen",
         ["Open the scene and request the viewer's normal fullscreen mode using a user gesture.", "Open/close and drag the overlay; then exit fullscreen."],
         "The overlay remains visible, interactive and bounded in fullscreen and after exit without losing its current in-memory messages.",
         "apps/frontend/features/chat/CHAT_OVERLAY_MOUNT.md"),
    case("TC_A11Y_01", "Responsive layout and accessibility", "Manage focus, Escape and hidden-panel keyboard access",
         ["Open the widget with the keyboard and inspect initial focus.", "Close with Escape and tab through the page while it is closed."],
         "Opening focuses the composer; Escape closes the panel and returns focus to the launcher. The closed panel is inert/aria-hidden and its controls are not tabbable.",
         "apps/frontend/features/chat/components/ChatOverlayWidget.tsx"),
    case("TC_REG_01", "Responsive layout and accessibility", "Preserve the standalone chat and production build",
         ["Run the existing chat-request tests and npm run build from apps/frontend.", "Open /chat and /content/tapestry-test/s0 in the production server."],
         "Transport checks and the build succeed. Both routes load; mounting the overlay does not replace the standalone chat or introduce duplicate widgets on the scene route.",
         "apps/frontend/tests/chat-request.test.mjs"),
]


def revision(ref="HEAD"):
    result = subprocess.run(["git", "rev-parse", ref], cwd=ROOT, text=True,
                            capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else "Not available"


def font(bold=False, size=11, color="000000"):
    return Font(name="Times New Roman", size=size, bold=bold, color=color)


def merge(ws, cell_range, value, bold=False):
    ws.merge_cells(cell_range)
    first = ws[cell_range.split(":")[0]]
    first.value = value
    first.font = font(bold)
    first.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def estimated_lines(value, width):
    return sum(max(1, len(wrap(line, width=max(8, int(width - 3)),
                              break_long_words=True, break_on_hyphens=False)))
               for line in str(value or "").split("\n"))


def add_form(wb, name, module, precondition, cases, source_revision):
    ws = wb.create_sheet(name)
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = 70
    ws.sheet_properties.tabColor = {"Search FUT": "38761D", "Chat Backend FUT": "1C4587",
                                    "Tour Chat FUT": "B45F06"}[name]
    for index, width in enumerate(WIDTHS, 1):
        ws.column_dimensions[chr(64 + index)].width = width
    ws["A1"], ws["A2"], ws["A3"] = "Module Code", "Tester", "Pre-condition"
    merge(ws, "B1:G1", module)
    merge(ws, "B2:G2", TESTER)
    merge(ws, "B3:G3", precondition)
    ws["A4"], ws["B4"] = "Pass", "Fail"
    merge(ws, "C4:G4", "Number of test case", True)
    last = 8 + len(cases)
    ws["A5"] = f'=COUNTIF(F9:F{last},"Pass")'
    ws["B5"] = f'=COUNTIF(F9:F{last},"Fail")'
    merge(ws, "C5:G5", f"=COUNTA(A9:A{last})")
    for row in ws.iter_rows(min_row=1, max_row=5, max_col=7):
        for cell in row:
            cell.border = BORDER
            cell.font = font(cell.row == 4 or cell.column == 1 and cell.row <= 3)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for cell in ws[7]:
        cell.border = BORDER
        cell.font = font(True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for i, label in enumerate(HEADERS, 1):
        ws.cell(7, i, label)
    merge(ws, "A8:G8", module, True)
    ws["A8"].font = font(True, color="B45F06")
    for row_num, item in enumerate(cases, 9):
        values = (item["id"], item["description"], item["procedure"], item["expected"],
                  None, "Not Run", None)
        for col_num, value in enumerate(values, 1):
            cell = ws.cell(row_num, col_num, value)
            cell.font = font(col_num == 1)
            cell.border = BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=True,
                                       horizontal="center" if col_num in (6, 7) else "left")
        ws.cell(row_num, 7).number_format = "dd/mm/yyyy"
        ws.row_dimensions[row_num].height = max(64, 16 * max(
            estimated_lines(values[i], WIDTHS[i]) for i in (1, 2, 3)) + 10)
        references = item.get("tests", [item.get("source", "")])
        ws.cell(row_num, 1).comment = Comment(
            f"Acceptance area: {item['group']}\nSource revision: {source_revision}\n"
            + "\n".join(references), "Heritage QA")
        ws.cell(row_num, 5).comment = Comment(
            "Not executed for this workbook. Enter the observed HTTP status/UI or database outcome, "
            "environment and evidence reference after running the procedure. Existing test references "
            "describe coverage; they are not a new passing result.", "Heritage QA")
    validation = DataValidation(type="list", formula1='"Pass,Fail,Blocked,Not Run"',
                                allow_blank=False)
    validation.errorTitle = "Choose a supported result"
    validation.error = "Use Pass, Fail, Blocked or Not Run."
    validation.showErrorMessage = True
    validation.errorStyle = "stop"
    validation.showDropDown = False
    validation.promptTitle = "Execution result"
    validation.prompt = "Record a result only after executing this case."
    validation.showInputMessage = True
    ws.add_data_validation(validation)
    validation.add(f"F9:F{last}")
    for state, (background, foreground) in STATES.items():
        ws.conditional_formatting.add(f"F9:F{last}", CellIsRule(
            operator="equal", formula=[f'"{state}"'], fill=PatternFill("solid", fgColor=background),
            font=font(True, color=foreground)))
    ws["A5"].fill = PatternFill("solid", fgColor="D9EAD3")
    ws["B5"].fill = PatternFill("solid", fgColor="F4CCCC")
    ws.row_dimensions[1].height = 26
    ws.row_dimensions[2].height = 23
    ws.row_dimensions[3].height = 64
    ws.row_dimensions[4].height = 22
    ws.row_dimensions[5].height = 22
    ws.row_dimensions[6].height = 10
    ws.row_dimensions[7].height = 32
    ws.row_dimensions[8].height = 25
    ws.freeze_panes = "C9"
    ws.print_title_rows = "1:8"
    ws.print_area = f"A1:G{last}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A3
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins = PageMargins(left=.2, right=.2, top=.3, bottom=.3, header=.1, footer=.1)
    ws.oddFooter.center.text = "Page &P of &N"
    ws.oddFooter.right.text = "Heritage | FUT"
    return ws


def add_notes(wb, modules, backend, current_revision):
    ws = wb.create_sheet("Execution Notes")
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 44
    for col in "BCDEFG":
        ws.column_dimensions[col].width = 22
    rows = [
        ("Purpose", "Functional/User Acceptance Test cases using the supplied seven-column form. All report text is English."),
        ("Prepared for", TESTER),
        ("Prepared on", datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%d/%m/%Y") + " (Asia/Ho_Chi_Minh; preparation date, not an execution date)"),
        ("Execution status", "All cases start as Not Run. Actual Result and Test Date are intentionally blank. This workbook does not certify a new test run or repeat an earlier manual sign-off."),
        ("Record evidence", "Execute the numbered steps. Enter the observed outcome in Actual Result, select Pass/Fail/Blocked/Not Run and enter the real test date. Attach a screenshot, HTTP response, log or test report reference; redact tokens and credentials."),
        ("Summary counters", "Pass and Fail count the Result column automatically. Number of test case counts case IDs. Not Run and Blocked are not counted as Pass or Fail."),
        ("Current frontend source", f"feat/HER-search-results-ui @ {current_revision}"),
        ("Chat Backend source", f"{backend['source_branch']} @ {backend['source_revision']}"),
        ("Branch boundary", "The current frontend branch has POST /api/chat only. The complete persisted conversation API exists in the separate Chat Backend source above. Run Chat Backend FUT against that API version. Do not interpret a missing route on the current branch as an executed failure of the separate implementation."),
        ("No implicit end-to-end claim", "Tour Chat FUT checks the legacy overlay as currently mounted. Its in-memory history is distinct from the backend's persisted account conversation history. Cross-branch persisted-history integration must be separately verified after integration."),
        ("Search environment", "Frontend http://localhost:3000/search; API GET http://localhost:8000/api/heritages. Use a nonempty published fixture catalogue for populated rows, categories, pagination and recommendations. Current search is client-side over the published catalogue, not a new OpenSearch search route."),
        ("Backend environment", "Use an approved isolated Postgres database with the chat migrations applied, two active accounts A/B, a Guest client, one published heritage and one draft heritage. Keep A/B access tokens separate. Use strict test/staging settings for timeout/failure cases; enable local fallback only for its dedicated cases."),
        ("Tour environment", "Frontend http://localhost:3000/content/tapestry-test/s0; existing scene s1; legacy API POST /api/chat. Use desktop plus 375x812 and 320x568 mobile sizes. A WebGL-capable browser is required for canvas interaction checks."),
        ("Backend request example", '{"message":"When was this heritage built?","conversation_id":null,"heritage_id":null,"heritage_context":{"title":"Test heritage"},"scene_context":"Main gate"}'),
        ("Guest continuation", "Persisted backend: a Guest can create a null-account conversation but cannot reuse its UUID to append/read/delete. Bounded client context may carry Guest context across independent requests. Authentication never adopts a Guest conversation automatically."),
        ("Context limits", "Backend context: up to 6 user/assistant messages, 2000 characters each, 6000 total; heritage_context and scene_context up to 2000 characters each; message up to 8000 characters. Existing saved conversation context is loaded by the server, not replaced by client history."),
        ("Backend success/error contract", "POST /api/chat/message -> 201; POST /api/chat -> 200; management read/list -> 200; owned delete -> 204; foreign ownership -> 403; absent UUID -> 404; invalid input -> 422; overall inference deadline -> 504. Strict persisted dependency/write failures return safe errors and roll back."),
        ("Existing automated Search checks", "From apps/frontend: node node_modules/tsx/dist/cli.mjs --test tests/heritage-search.test.ts"),
        ("Existing automated transport checks", "From apps/frontend: node --test tests/chat-request.test.mjs"),
        ("Existing automated backend checks", "On the Chat Backend branch, from root: python -m pytest apps/backend/tests/test_chat_api.py apps/backend/tests/test_chat_conversation.py apps/backend/tests/test_chat_fallback.py apps/backend/tests/test_chat_integration.py apps/backend/tests/test_chat_graphrag.py apps/backend/tests/test_llama_server.py apps/backend/tests/test_prompt.py -v"),
        ("Frontend production check", "From apps/frontend: npm run build; run one Next server per workspace build directory."),
        ("Failure injection", "Use browser request interception or existing isolated automated tests for HTTP failures, delayed inference, malformed payloads and commit failures. Never disrupt a shared/production service or use real account data for these cases."),
        ("Evidence boundaries", "Controlled model/provider responses verify API behavior, persistence and UI integration. They do not certify live model accuracy, current corpus quality, Gemini availability or production 3D assets. Validate those separately when required."),
        ("Regenerate", "With openpyxl installed: python generate_feature_fut.py. The generator performs no API calls, test runs, migrations or database writes. Regenerating resets every case to Not Run; preserve your completed execution copy separately."),
    ]
    merge(ws, "A1:G1", "Heritage FUT - Execution Guide and Scope", True)
    ws.row_dimensions[1].height = 30
    for r, (label, value) in enumerate(rows, 3):
        ws.cell(r, 1, label).font = font(True)
        merge(ws, f"B{r}:G{r}", value)
        ws.cell(r, 2).alignment = Alignment(vertical="center", wrap_text=True)
        ws.row_dimensions[r].height = max(32, estimated_lines(value, 126) * 16 + 8)
    row = len(rows) + 5
    merge(ws, f"A{row}:G{row}", "Acceptance Coverage", True)
    row += 1
    for name, _module, _precondition, cases, _rev in modules:
        for group in dict.fromkeys(item["group"] for item in cases):
            matching = [item["id"] for item in cases if item["group"] == group]
            ws.cell(row, 1, name).font = font(True)
            value = f"{group} ({len(matching)} cases): " + ", ".join(matching)
            merge(ws, f"B{row}:G{row}", value)
            ws.cell(row, 2).alignment = Alignment(vertical="center", wrap_text=True)
            ws.row_dimensions[row].height = max(32, estimated_lines(value, 126) * 16 + 8)
            row += 1
    for cells in ws.iter_rows(min_row=1, max_row=row - 1, max_col=7):
        for cell in cells:
            if cell.value is not None:
                cell.border = BORDER
                if cell.font.name != "Times New Roman":
                    cell.font = font()
    ws.freeze_panes = "B3"
    ws.sheet_properties.tabColor = "666666"
    ws.print_area = f"A1:G{row - 1}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def cache_initial_totals(path, counts):
    """Store correct initial formula previews for readers without a calc engine."""
    namespace = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(path) as original:
        entries = {item.filename: (item, original.read(item.filename)) for item in original.infolist()}
    for index, total in enumerate(counts, 1):
        filename = f"xl/worksheets/sheet{index}.xml"
        info, data = entries[filename]
        # Preserve openpyxl's namespace prefixes and document formatting.
        for cell_ref, value in {"A5": 0, "B5": 0, "C5": total}.items():
            pattern = rb'(<c\b[^>]*\br="' + cell_ref.encode() + rb'"[^>]*>.*?<f[^>]*>.*?</f>)(?:<v>.*?</v>|<v\s*/>)?(</c>)'
            data, changed = re.subn(pattern, lambda m: m[1] + f"<v>{value}</v>".encode() + m[2], data)
            if changed != 1:
                raise ValueError(f"Cannot cache {filename}:{cell_ref}")
        ET.fromstring(data).find("s:sheetData", namespace)  # Reject invalid XML before saving.
        entries[filename] = (info, data)
    temporary = path.with_suffix(".cached.xlsx")
    with ZipFile(temporary, "w", ZIP_DEFLATED) as output:
        for info, data in entries.values():
            output.writestr(info, data)
    temporary.replace(path)


def validate(path, modules):
    wb = load_workbook(path)
    values = load_workbook(path, data_only=True)
    assert len(wb.worksheets) == 4
    seen = set()
    for name, _module, _precondition, cases, _rev in modules:
        ws = wb[name]
        assert tuple(ws.cell(7, i).value for i in range(1, 8)) == HEADERS
        assert values[name]["C5"].value == len(cases)
        assert values[name]["A5"].value == values[name]["B5"].value == 0
        assert len(ws.data_validations.dataValidation) == 1
        assert ws.freeze_panes == "C9"
        for row, item in enumerate(cases, 9):
            assert item["id"] not in seen
            seen.add(item["id"])
            assert ws.cell(row, 1).value == item["id"]
            assert all(ws.cell(row, i).value for i in (2, 3, 4))
            assert ws.cell(row, 5).value is None
            assert ws.cell(row, 6).value == "Not Run"
            assert ws.cell(row, 7).value is None
            assert ws.row_dimensions[row].height <= 409
    assert not wb._external_links
    with ZipFile(path) as archive:
        assert archive.testzip() is None
        for filename in archive.namelist():
            if filename.endswith(".xml"):
                ET.fromstring(archive.read(filename))
    wb.close()
    values.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "FUT_Search_Chat_Backend_Tour.xlsx")
    args = parser.parse_args()
    path = args.output.resolve()
    if path.exists():
        raise SystemExit(f"Refusing to overwrite an existing execution workbook: {path}. Use --output with a new filename.")
    backend = json.loads((ROOT / "docs/testing/chat-backend-fut-cases.json").read_text(encoding="utf-8"))
    current_revision = revision()
    modules = [
        ("Search FUT", "Implement Advanced Heritage Search and Filtering",
         "Frontend and GET /api/heritages are running. Prepare published catalogue fixtures with explicit categories, multiple regions and at least 23 tours for pagination. Use desktop/mobile browsers and request interception for failure cases.",
         SEARCH_CASES, current_revision),
        ("Chat Backend FUT", backend["module"],
         "Run the separate Chat Backend source listed in Execution Notes. Approved isolated PostgreSQL schema is migrated; active accounts A/B and separate JWTs are available. Prepare published/draft heritage fixtures and controlled retrieval/model responses. No frontend is required.",
         backend["cases"], backend["source_revision"]),
        ("Tour Chat FUT", "Integrate the Chat Interface into Tour Scenes",
         "Frontend /content/tapestry-test/s0 and legacy POST /api/chat are available. Use a WebGL-capable browser, scene s1, Guest/member sessions and desktop/mobile viewports. Delay/fail model/API requests only through isolated test interception.",
         TOUR_CASES, current_revision),
    ]
    wb = Workbook()
    wb.remove(wb.active)
    wb.properties.title = "Heritage Functional and User Acceptance Tests"
    wb.properties.creator = TESTER
    wb.properties.description = "English FUT cases; unexecuted template with no fabricated results."
    wb.calculation = CalcProperties(calcId=191029, fullCalcOnLoad=True, forceFullCalc=True, calcMode="auto")
    for module in modules:
        add_form(wb, *module)
    add_notes(wb, modules, backend, current_revision)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    wb.close()
    cache_initial_totals(path, [len(module[3]) for module in modules])
    validate(path, modules)
    print(path)
    for name, _module, _precondition, cases, _rev in modules:
        print(f"{name}: {len(cases)} cases; " + ", ".join(f"{k}={v}" for k, v in Counter({"Not Run": len(cases), "Pass": 0, "Fail": 0}).items()))
    print("Workbook validation passed: structure, cached totals, case IDs, result dropdowns, blank execution fields and XML integrity.")


if __name__ == "__main__":
    main()
