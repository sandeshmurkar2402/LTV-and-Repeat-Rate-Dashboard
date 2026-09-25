import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import charts as ch
import data_loader as dl
import data_processing as dp

st.set_page_config(page_title="LTV & Repeat Rate Dashboard", layout="wide", page_icon="\U0001F4C8")

CUSTOM_CSS = """
<style>
    .stApp {
        background: linear-gradient(180deg, #eef3fb 0%, #f6f8fc 320px, #f6f8fc 100%);
    }
    .block-container {
        padding-top: 0.7rem;
        padding-bottom: 2rem;
        max-width: 1550px;
    }
    div[data-testid="stVerticalBlock"] {
        gap: 0.6rem;
    }
    /* Streamlit's own header is a fixed, opaque, 60px bar (z-index 999990) that
       sits above the page regardless of scroll. With a small padding-top it was
       painting over our title and Refresh button instead of just sitting behind
       them — making it transparent lets our content show through cleanly. It was
       still intercepting clicks meant for the button even once invisible, though
       (a transparent element still blocks pointer events by default) — every one
       of its own children (menu, deploy, toolbar) is already hidden elsewhere in
       this stylesheet, so it has nothing left to be clickable for; pointer-events:
       none lets clicks fall through to whatever is actually underneath it. */
    header[data-testid="stHeader"] {
        background: transparent;
        pointer-events: none;
    }
    div[data-testid="stStatusWidget"] { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    h1, h2, h3 { margin-top: 0.1rem; margin-bottom: 0.3rem; color: #12233f; }
    div[data-testid="stCaptionContainer"] { margin-bottom: 0; }
    hr { margin: 0.4rem 0 !important; }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px;
    }
    div[data-testid="stElementContainer"] div[data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e1e7f0;
    }
    /* st.table (used for the heatmap tables so the header row can be colored —
       st.dataframe's header is canvas-rendered and ignores Styler CSS entirely) */
    div[data-testid="stTable"] {
        border-radius: 12px;
        overflow-x: auto;
        border: 1px solid #e1e7f0;
    }
    /* table-layout: auto sizes each column to its own widest cell (header or data).
       The "New" header is short on purpose (was "New Acquisitions") so that column
       is sized by its currency values, not by its own header text — previously the
       17-char header outsized the data and made the column balloon. width: 100%
       then lets any remaining slack spread across columns in proportion to what
       each one actually needs, instead of leaving dead space on the right.
       nowrap + the container's overflow-x keeps values on one line at any screen
       width; the table scrolls horizontally rather than wrapping mid-number. */
    div[data-testid="stTable"] table {
        table-layout: auto;
        width: 100%;
    }
    div[data-testid="stTable"] table th,
    div[data-testid="stTable"] table td {
        white-space: nowrap;
        text-align: center;
    }
    /* Month/Period is this table's row index, rendered as the first <th> of
       each body row (plus the blank corner cell above it in <thead>) — kept
       left-aligned, same rule the outline tables apply via .outline-label-cell;
       every other header/value cell (New, M0, M1, ...) is centered. */
    div[data-testid="stTable"] table thead th:first-child,
    div[data-testid="stTable"] table tbody th:first-child {
        text-align: left;
    }

    /* --- toolbar rows (tabs / filters) --- */
    /* Match the segmented-control button height to the taller bordered selectbox
       chips (40px) so each row lines up instead of looking uneven. */
    div[data-testid="stButtonGroup"] button[data-testid^="stBaseButton-segmented_control"] {
        border-radius: 8px !important;
        font-weight: 600 !important;
        min-height: 40px !important;
        display: flex !important;
        align-items: center !important;
        white-space: nowrap !important;
        flex-shrink: 0 !important;
    }
    /* Never let a control's own pills wrap onto a second line — keep them on one row.
       With 8 top-level tabs now, narrow screens scroll horizontally instead. */
    .st-key-tab_nav div[data-testid="stButtonGroup"],
    .st-key-mode_toggle div[data-testid="stButtonGroup"] {
        flex-wrap: nowrap !important;
    }
    .st-key-tab_nav {
        overflow-x: auto;
    }
    /* Any segmented control's active option: filled green by default, everywhere —
       Value (Revenue/Users/Purchases), Component (Overall/New/Repeat), Absolute/%
       toggles, etc. — so "what's currently selected" always reads the same way at
       a glance, regardless of which control it is.
       NOTE: Streamlit's segmented_control never sets aria-checked on these buttons —
       the actual selected-state marker is kind="segmented_controlActive" (verified via
       live DOM inspection); a prior [aria-checked="true"] selector was dead code that
       never matched anything. */
    div[data-testid="stButtonGroup"] button[kind="segmented_controlActive"],
    div[data-testid="stButtonGroup"] button.force-active {
        background-color: #1baf7a !important;
        color: #ffffff !important;
        border-color: #1baf7a !important;
    }
    /* Section tabs are the one exception — kept blue to visually separate top-level
       navigation from in-tab filter toggles. */
    .st-key-tab_nav div[data-testid="stButtonGroup"] button[kind="segmented_controlActive"],
    .st-key-tab_nav div[data-testid="stButtonGroup"] button.force-active {
        background-color: #2a78d6 !important;
        border-color: #2a78d6 !important;
    }
    .st-key-mode_toggle div[data-testid="stButtonGroup"] button {
        min-width: 108px !important;
        justify-content: center !important;
    }

    /* Filter dropdowns: give them a visible tinted, bordered "chip" so they read as
       interactive controls instead of blending into the page (previously a blind spot). */
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        background-color: #eaf2fd !important;
        border: 1.6px solid #2a78d6 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    div[data-testid="stSelectbox"] div[data-baseweb="select"]:hover > div {
        border-color: #184f95 !important;
    }

    /* checkbox_multiselect's popover trigger button — same tinted chip as the
       selectboxes above, so it reads as the same family of control. Forced to a
       single line (ellipsized rather than wrapped) so it always matches the
       fixed-height selectboxes/segmented controls next to it in the same row —
       a long label like "Platform: ANDROID" was wrapping onto 2 lines otherwise,
       making that one control taller than its neighbors. */
    button[data-testid="stPopoverButton"] {
        background-color: #eaf2fd !important;
        border: 1.6px solid #2a78d6 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        min-height: 40px !important;
        height: 40px !important;
        max-height: 40px !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        overflow: hidden !important;
    }
    button[data-testid="stPopoverButton"]:hover {
        border-color: #184f95 !important;
    }
    /* This whole block (including the rule above) was silently not applying
       at all — `div[data-testid="stPopover"] > button` used a direct-child
       combinator, but Streamlit actually wraps the real button one level
       deeper (stPopover > an unlabeled aria-haspopup div > the button), so
       that selector never matched anything, ever; only invisible so long as
       every real label happened to be short enough to fit regardless.
       Targeting the button's own data-testid instead makes this immune to
       that nesting. Streamlit also wraps the label text in a
       stMarkdownContainer div, not just a <p> (same gap the L1/L2/L3
       outline-toggle-button fix hit), and that container needs min-width: 0
       or a flex child is allowed to grow past its parent's fixed width
       instead of actually truncating — the compact 3-4 dim cohort filter
       columns made this matter in practice, since "Group Online" no longer
       had much slack next to the dropdown chevron icon. */
    button[data-testid="stPopoverButton"] p,
    button[data-testid="stPopoverButton"] div[data-testid="stMarkdownContainer"] {
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        min-width: 0 !important;
        display: block !important;
        width: 100% !important;
    }

    /* Session Month / Purchase Month's single packed filter row — every control in
       it gets a smaller font and tighter padding so up to 7 controls comfortably
       fit on one line. */
    .st-key-pm_row div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    .st-key-pm_row button[data-testid="stPopoverButton"],
    .st-key-pm_row div[data-testid="stButtonGroup"] button,
    .st-key-pm_row label p {
        font-size: 0.78rem !important;
    }
    .st-key-pm_row div[data-testid="stButtonGroup"] button {
        padding: 0.2rem 0.45rem !important;
        min-height: 34px !important;
    }
    .st-key-pm_row button[data-testid="stPopoverButton"],
    .st-key-pm_row div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        min-height: 34px !important;
        height: 34px !important;
    }
    .st-key-pm_row div[data-testid="stButtonGroup"] {
        flex-wrap: nowrap !important;
    }

    div[data-testid="stToolbar"] { visibility: hidden; }

    /* --- Outline tables (Google-Sheets-style per-period +/- row grouping) --- */
    /* The +/- toggle is a real st.button, restyled to read as a plain inline
       glyph+label rather than a bulky button, so the whole thing reads as one
       cohesive table instead of a row of separate widgets. Scoped via a
       substring match on the wrapping container's key (every outline table's
       st.container key starts with "outline_") rather than repeating this CSS
       per table instance. */
    div[class*="st-key-outline_"] div[data-testid="stVerticalBlockBorderWrapper"],
    div[class*="st-key-outline_"] { gap: 0 !important; }
    div[class*="st-key-outline_"] div[data-testid="stButton"] button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 6px 10px !important;
        min-height: 0 !important;
        height: auto !important;
        width: 100% !important;
        font-weight: 600 !important;
        color: #12233f !important;
        font-size: 0.85rem !important;
        text-align: left !important;
        justify-content: flex-start !important;
    }
    div[class*="st-key-outline_"] div[data-testid="stButton"] button:hover {
        color: #2a78d6 !important;
        background: #eaf2fd !important;
    }
    div[class*="st-key-outline_"] div[data-testid="stButton"] {
        display: flex;
        align-items: stretch;
    }
    .outline-wrap {
        border: 1px solid #e1e7f0;
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 0.5rem;
        background: #ffffff;
    }
    .outline-row {
        display: flex;
        width: 100%;
        align-items: stretch;
    }
    .outline-header-row {
        background: #4a0404 !important;
        color: #ffffff !important;
        font-weight: 700;
        min-height: 2.2rem;
    }
    .outline-agg-row {
        font-weight: 600;
        background: #f7f9fc;
        border-top: 1px solid #e1e7f0;
        min-height: 2.2rem;
    }
    .outline-sub-row {
        color: #6b6b6b;
        font-weight: 400;
        font-size: 0.85rem;
        background: #ffffff;
        border-top: 1px solid #f1f3f7;
        min-height: 2rem;
    }
    /* Second-level sub-row (e.g. CM Business Line nested under an expanded
       Acquisition Business Line, or Acquisition Platform nested under one) —
       a faint tint plus deeper indent (set on .outline-label-cell inline via
       extra &nbsp;s) visually separates it from its L1 parent row above,
       reinforcing the "Acq BL:"/"CM BL:" text prefixes that already disambiguate
       which dimension each row's value belongs to. */
    .outline-sub-row-l2 {
        background: #fafbfd;
        font-size: 0.8rem;
    }
    /* Third-level sub-row (Cross Sales (Platform x Acq BL)'s CM Business Line,
       nested under an expanded Acquisition Platform, itself nested under an
       expanded Acquisition Business Line) — one tint step further and a
       deeper indent, continuing the same visual hierarchy as L1/L2. */
    .outline-sub-row-l3 {
        background: #f5f7fb;
        font-size: 0.78rem;
        color: #8a8f9a;
    }
    /* Fourth-level sub-row (Cross Sales (Platform x Acq BL)'s CM Platform,
       nested under an expanded CM Business Line) — the deepest tier/indent. */
    .outline-sub-row-l4 {
        background: #f0f3f9;
        font-size: 0.76rem;
        color: #a0a5b0;
    }
    /* Every value cell (New, M0, M1, ...) of a given row lives inside this one
       grid wrapper — a period row's real st.columns rcol renders ONLY this
       (no label cell: the button in lcol is that row's label), while the
       header row and expanded sub-rows render it as a flex sibling next to
       their own .outline-label-cell. Giving every row's value area the SAME
       grid-template-columns (set on every .outline-value-cells by the
       outlineColumnFix script below, from each column's real max content
       width) is what keeps New/M0/M1/... lined up across header, collapsed,
       and expanded rows — a per-row-guessed flex ratio can't guarantee that,
       which is exactly what caused the earlier left-alignment drift. The
       equal-width grid-auto-columns here is only the placeholder shown for
       the brief instant before that script's first pass measures real content. */
    .outline-value-cells {
        flex: 1 1 auto;
        min-width: 0;
        display: grid;
        grid-auto-flow: column;
        grid-auto-columns: minmax(0, 1fr);
        align-items: stretch;
        /* Columns never shrink below their own real content (minmax(px, 1fr) in
           the outlineColumnFix script below) — usually that content fits fine
           and 1fr just fills any leftover space, but a wide date range can push
           real M12+ values (a big currency number) past what this row's real
           Streamlit column width actually is. Without this, the grid simply
           grew past its box with nothing to contain it — the overflow spilled
           onto the plain page background with no row background behind it,
           looking exactly like a missing/broken column. Scrolling instead of
           overflowing keeps every column inside a visibly bordered row; the
           scroll-sync in that same script keeps every row (and the header)
           scrolled to the same position so columns stay aligned. */
        overflow-x: auto;
        scrollbar-width: thin;
    }
    .outline-cell {
        min-width: 0;
        text-align: center;
        padding: 6px 5px;
        font-size: 0.85rem;
        display: flex;
        align-items: center;
        justify-content: center;
        line-height: 1.3;
        white-space: nowrap;
        /* No overflow:hidden/ellipsis on purpose — the outlineColumnFix script
           sizes every column to at least its own widest cell's natural
           (scrollWidth) content, so nothing here should ever need clipping. */
    }
    /* Header cells stay single-line (NOT wrapped to 2 lines) on purpose — a
       taller-than-one-line header is exactly what previously made Streamlit
       under-measure its wrapping container (sized off a single-line default)
       and overlap the row below it. A smaller font/tighter padding here
       instead gives "8-14 Days" etc. enough room to fit on the one line. */
    .outline-header-row .outline-cell {
        font-size: 0.74rem;
        padding: 6px 4px;
        letter-spacing: -0.01em;
    }
    .outline-label-cell {
        /* Placeholder width only — the outlineColumnFix script overwrites this
           with the real, on-screen pixel width of the period row's own button
           column (an actual st.columns split) so the label column of the
           header row and every expanded sub-row starts and ends at exactly
           the same x as that button, instead of an approximated ratio drifting
           away from Streamlit's real column gap/padding. Left-aligned — the
           one column (Month/Period) that stays left rather than centered. */
        flex: 0 0 100px;
        min-width: 0;
        text-align: left;
        justify-content: flex-start;
        padding: 6px 8px;
        /* Unlike the value cells, this column's width is pinned to match a
           short period-name button — never widened to fit content — so an
           outlier long category name (e.g. a business line called
           "INCOMPLETE_DATA_WHILE_PAYMENT_RECONCILIATION") is allowed to wrap
           onto multiple lines instead of being cropped; the row-height
           self-healing script above already re-measures and grows the row to
           fit however many lines that takes. */
        white-space: normal;
        word-break: break-word;
        line-height: 1.25;
    }
    .outline-diff-pos { color: #0d5c3f; background-color: #e6f7ef; font-weight: 700; }
    .outline-diff-neg { color: #8a1f1f; background-color: #fdeaea; font-weight: 700; }
    .outline-emphasize { border-left: 3px solid #12233f; font-weight: 700; }
    /* L1/L2/L3 toggle buttons in the multi-level outline (Cross Sales / Cross
       Sales (Platform x Acq BL)) are a real st.button in the same label column
       a period button uses — fine for "Feb-2026", but a longer category name
       (e.g. "Group Online") wrapped onto 2 lines by default, making that row
       noticeably taller than its neighbors. Smaller font + no-wrap keeps every
       row the same height as a period row; the label column itself
       (st.columns([1.3, 8.7]) above) is wide enough for the common case, so
       nothing needs to scroll — an earlier overflow-x: auto fallback for
       outlier-long names showed a permanent scrollbar on ordinary rows too,
       looking like a stray thick border between rows, so it's gone in favor of
       just a wider column. (L4, the deepest level, never has its own button —
       it's always the plain-markdown leaf level — so only L1/L2/L3 need this.) */
    div[class*="_l1_toggle"] button p, div[class*="_l2_toggle"] button p, div[class*="_l3_toggle"] button p,
    div[class*="_l1_toggle"] button div[data-testid="stMarkdownContainer"],
    div[class*="_l2_toggle"] button div[data-testid="stMarkdownContainer"],
    div[class*="_l3_toggle"] button div[data-testid="stMarkdownContainer"] {
        font-size: 0.78rem !important;
        white-space: nowrap !important;
    }
    div[class*="st-key-outline_"] div[data-testid="stHorizontalBlock"] {
        align-items: stretch !important;
    }
    /* Streamlit sizes a markdown element's wrapping container off its default
       single-line text height; our padded, multi-cell HTML rows are taller
       than that reserved space, so — without this — each row's real (taller)
       content visually overflows into the next row's reserved slot instead of
       pushing it down, making consecutive sub-rows overlap. */
    div[class*="st-key-outline_"] div[data-testid="stElementContainer"],
    div[class*="st-key-outline_"] div[data-testid="stMarkdown"],
    div[class*="st-key-outline_"] div[data-testid="stMarkdownContainer"] {
        height: auto !important;
        min-height: 0 !important;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Segmented controls sometimes render one rerun "behind" on which button shows
# as visually active — e.g. AOV/ARPU replace the Absolute/%Contrib toggle with a
# caption, and that widget's DOM position shifting seems to be enough for
# Streamlit's own active-button attribute patch to lag a render (the underlying
# selection/data is always correct immediately; only the highlight color lags,
# and only catches up once something else forces a full re-render, e.g. switching
# tabs and back). Rather than chase Streamlit's own diffing internals, a plain
# capture-phase click listener marks the clicked button active the instant it's
# clicked — before Streamlit's rerun round-trip even starts — so the highlight
# never has anything to lag behind in the first place.
components.html(
    """
    <script>
    (function() {
      const doc = window.parent.document;
      if (doc.__segmentedActiveFix) return;
      doc.__segmentedActiveFix = true;

      // Which option (by button text) was last clicked, per button-group element.
      // A plain class added once gets wiped the instant Streamlit's own React
      // re-render replaces that button node in response to the same click — so
      // instead of a one-shot class add, a MutationObserver keeps re-applying it
      // to whichever button currently has the remembered text, self-healing
      // through however many DOM replacements Streamlit's rerun causes.
      const lastClicked = new WeakMap();

      function applyActive(group) {
        const wanted = lastClicked.get(group);
        if (wanted === undefined) return;
        group.querySelectorAll('button').forEach(function(b) {
          const shouldHave = b.textContent.trim() === wanted;
          if (shouldHave && !b.classList.contains('force-active')) b.classList.add('force-active');
          if (!shouldHave && b.classList.contains('force-active')) b.classList.remove('force-active');
        });
      }

      doc.addEventListener('click', function(e) {
        const btn = e.target.closest('button[data-testid^="stBaseButton-segmented_control"]');
        if (!btn) return;
        const group = btn.closest('div[data-testid="stButtonGroup"]');
        if (!group) return;
        lastClicked.set(group, btn.textContent.trim());
        applyActive(group);
      }, true);

      new MutationObserver(function(mutations) {
        mutations.forEach(function(m) {
          const group = m.target.closest && m.target.closest('div[data-testid="stButtonGroup"]');
          if (group && lastClicked.has(group)) applyActive(group);
        });
      }).observe(doc.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['kind', 'class'] });
    })();
    </script>
    """,
    height=0,
)

# The outline tables' rows (render_outline_table / render_outline_diff_table)
# are plain HTML injected via st.markdown(unsafe_allow_html=True). Streamlit
# sizes that markdown element's own wrapping container off an internal
# estimate (apparently keyed to something like "how tall did content at this
# position look before", not the actual rendered content) rather than the
# real height of our (taller, padded, multi-cell) row(s) — so a wrapper
# sometimes reserves less vertical space than its content needs, and the
# excess visually spills into whatever renders next (adjacent rows overlapping
# instead of stacking, or table text getting clipped). Batching many rows into
# one markdown call mostly avoids it, but not always (e.g. a lone header row).
# Rather than keep chasing which exact shapes trigger Streamlit's estimate to
# be wrong, this measures every such wrapper's *actual* rendered content
# height directly and pins the wrapper to match — self-healing through
# reruns/DOM-replacement the same way the segmented-control fix above does.
components.html(
    """
    <script>
    (function() {
      const doc = window.parent.document;
      if (doc.__outlineRowHeightFix) return;
      doc.__outlineRowHeightFix = true;

      function fixOne(container) {
        // .outline-row descendants (not just direct children — Streamlit
        // nests our markdown inside its own stMarkdown/stMarkdownContainer
        // wrapper divs first) are exactly the rows this one markdown call
        // rendered; summing their real heights reconstructs what the
        // container actually needs.
        const rows = container.querySelectorAll('.outline-row');
        let total = 0;
        rows.forEach(function(r) { total += r.getBoundingClientRect().height; });
        if (total > 0) {
          const px = Math.ceil(total) + 'px';
          if (container.style.height !== px) {
            container.style.setProperty('height', px, 'important');
            container.style.setProperty('min-height', px, 'important');
          }
        }
      }

      function fixAll() {
        doc.querySelectorAll('div[class*="st-key-outline_"] div[data-testid="stElementContainer"]').forEach(function(el) {
          if (el.querySelector('.outline-row')) fixOne(el);
        });
      }

      new MutationObserver(fixAll).observe(doc.body, { childList: true, subtree: true });
      // Layout can settle a frame or two after the mutation itself (fonts/
      // reflow), so also re-check on a short interval as a safety net.
      setInterval(fixAll, 250);
    })();
    </script>
    """,
    height=0,
)

# Outline tables' columns (New/M0/M1/.../header cells) must line up exactly
# across 3 differently-built row kinds: the header row and every expanded
# sub-row are one flex row with a label cell + a value-cells block built
# directly in Python, while a collapsed period row's "label" is instead a REAL
# st.button living in its own st.columns() column, with only the value cells
# rendered as markdown next to it. Approximating that button column's pixel
# width from its column ratio (1.3:8.7) drifts from Streamlit's own real
# column gap/padding — this measures the actual on-screen geometry instead and
# copies it, the same self-healing/measure-and-pin approach as the height fix
# above. It also sizes every column (via CSS Grid) to the widest real content
# (scrollWidth) seen anywhere in that column across every row kind, so nothing
# in New/M0/M1/... ever gets cropped.
components.html(
    """
    <script>
    (function() {
      const doc = window.parent.document;
      if (doc.__outlineColumnFix) return;
      doc.__outlineColumnFix = true;

      function fixOne(scope) {
        const valueWraps = Array.from(scope.querySelectorAll('.outline-value-cells'));
        if (!valueWraps.length) return;

        // 1) Column widths: widest real content (header cells, collapsed-row
        // cells, and expanded-sub-row cells all count) at each column index,
        // anywhere in this one table.
        let nCols = 0;
        valueWraps.forEach(function(r) { nCols = Math.max(nCols, r.children.length); });
        if (nCols > 0) {
          // Measure each cell's natural content width via a detached, hidden
          // CLONE — never the live cell itself. Three failure modes this
          // avoids, all seen in earlier versions of this script: (a) measuring
          // a live cell that's still stretched from the last pass's own pixel
          // template and padding that measurement again made columns grow
          // without bound every 250ms; (b) even after fixing that by resetting
          // the live grid-template-columns before measuring, mutating that
          // style on every 250ms tick reset each row's scroll position back to
          // 0 (needed now that .outline-value-cells can scroll horizontally —
          // see its CSS above), making it impossible to actually scroll to a
          // column past the visible edge; (c) appending/removing the measuring
          // clone directly under doc.body — the exact subtree this script's
          // own MutationObserver watches — made every single measurement
          // trigger that same observer, which measured again, appending and
          // removing more clones, forever: an infinite synchronous loop that
          // froze the tab solid. The fix for (c) is this one persistent host
          // element, created once, attached to <html> itself rather than
          // <body> — a sibling of the observed subtree, not a descendant of
          // it — so appending/removing measurement clones inside it can never
          // register as a mutation of doc.body's subtree in the first place.
          let measureHost = doc.getElementById('__outlineMeasureHost');
          if (!measureHost) {
            measureHost = doc.createElement('div');
            measureHost.id = '__outlineMeasureHost';
            measureHost.style.position = 'absolute';
            measureHost.style.visibility = 'hidden';
            measureHost.style.left = '-99999px';
            measureHost.style.top = '0';
            measureHost.style.pointerEvents = 'none';
            doc.documentElement.appendChild(measureHost);
          }
          const maxW = new Array(nCols).fill(0);
          valueWraps.forEach(function(r) {
            Array.from(r.children).forEach(function(cell, i) {
              const clone = cell.cloneNode(true);
              clone.style.width = 'auto';
              measureHost.appendChild(clone);
              maxW[i] = Math.max(maxW[i], clone.offsetWidth);
              measureHost.removeChild(clone);
            });
          });
          // minmax(contentPx, 1fr), not a bare px value: a column is never
          // squeezed below its own real content (which is what let numbers
          // overflow past the last column in some Absolute-value tables), but
          // when the table is wider than the sum of every column's natural
          // content width, the 1fr half lets every column share that leftover
          // space equally instead of leaving it as blank space after the last
          // column — the same "table-layout: auto; width: 100%" behavior the
          // plain st.table heatmap (used for the Overall view) already gets
          // for free from the browser's native table layout algorithm.
          const template = maxW.map(function(w) { return 'minmax(' + Math.ceil(w + 4) + 'px, 1fr)'; }).join(' ');
          valueWraps.forEach(function(r) {
            if (r.style.gridTemplateColumns !== template) r.style.gridTemplateColumns = template;
          });
        }

        // 1b) Scroll-sync: .outline-value-cells now scrolls horizontally
        // (CSS) instead of overflowing past the table's border when a column's
        // real content is wider than this row's actual available space (a wide
        // date range can make M12+ a large currency number, wider than what
        // Streamlit's own real st.columns rcol gives this row). Each row/the
        // header is its own independent scroll container, so without this,
        // scrolling one wouldn't move the others and columns would stop lining
        // up — this mirrors any one row's scrollLeft onto every other row (and
        // the header) in the same table. Re-queries scope fresh inside the
        // handler (not the valueWraps captured above) so it still finds rows
        // added later by expanding a period.
        valueWraps.forEach(function(w) {
          if (w.__outlineScrollSync) return;
          w.__outlineScrollSync = true;
          w.addEventListener('scroll', function() {
            const left = w.scrollLeft;
            scope.querySelectorAll('.outline-value-cells').forEach(function(other) {
              if (other !== w && other.scrollLeft !== left) other.scrollLeft = left;
            });
          });
        });

        // 2) Label-cell width: copy wherever a real period row's value
        // columns actually start on screen (that row's .outline-value-cells is
        // the ONLY child of its .outline-row — no label cell next to it, since
        // the button in st.columns' own lcol already is that row's label) — an
        // empirical match, not a guess at Streamlit's own column gap/padding.
        const refWrap = valueWraps.find(function(r) { return r.parentElement.children.length === 1; });
        if (!refWrap) return;
        const targetLeft = refWrap.getBoundingClientRect().left;
        scope.querySelectorAll('.outline-row').forEach(function(row) {
          const labelCell = row.querySelector(':scope > .outline-label-cell');
          if (!labelCell) return;
          const width = Math.round(targetLeft - row.getBoundingClientRect().left);
          if (width > 0) {
            const px = width + 'px';
            if (labelCell.style.flexBasis !== px) labelCell.style.flex = '0 0 ' + px;
          }
        });
      }

      function fixAll() {
        doc.querySelectorAll('div[class*="st-key-outline_"]').forEach(fixOne);
      }

      new MutationObserver(fixAll).observe(doc.body, { childList: true, subtree: true });
      setInterval(fixAll, 250);
    })();
    </script>
    """,
    height=0,
)


def checkbox_multiselect(label, options, key, default=None):
    """Compact stand-in for st.multiselect: a small popover button showing a short
    summary ('All' / the one picked name / 'N selected') instead of Streamlit's
    chip list, with a checkbox per option plus Select all / Clear all inside.

    Purely option-driven — nothing here assumes a fixed number of business lines
    or platforms, so a new one showing up in the sheet just becomes a new row the
    next time `options` includes it; no code change needed.

    The actual selection lives in st.session_state[f"{key}__persisted"], a plain
    dict entry re-applied to each checkbox on every render — NOT in the checkboxes'
    own widget state. Streamlit silently resets a keyed widget back to its default
    if that widget isn't rendered for one or more reruns (e.g. the user switched to
    a different tab where this control's code path doesn't run at all); re-seeding
    from our own persisted copy every time is what survives that."""
    options = list(options)
    default = list(default) if default else list(options)
    persist_key = f"{key}__persisted"
    if persist_key not in st.session_state:
        st.session_state[persist_key] = list(default)
    st.session_state[persist_key] = [v for v in st.session_state[persist_key] if v in options]

    cb_keys = {opt: f"{key}_cb_{opt}" for opt in options}

    def _sync():
        st.session_state[persist_key] = [opt for opt in options if st.session_state.get(cb_keys[opt], False)]

    for opt, ck in cb_keys.items():
        st.session_state[ck] = opt in st.session_state[persist_key]

    current = st.session_state[persist_key]
    if not options:
        summary = "—"
    elif len(current) == len(options):
        summary = "All"
    elif len(current) == 0:
        summary = "None"
    elif len(current) == 1:
        # Just the picked value, no "{label}: " prefix — with a longer dimension
        # label (e.g. "Acquisition Business Line") that prefix was what made the
        # trigger button's text (and therefore the whole popover chip) balloon in
        # width; the button sits in a fixed-position column next to other
        # controls regardless of which single value is picked, so the label
        # itself adds nothing a user watching that column position can't already
        # tell.
        summary = current[0]
    else:
        summary = f"{len(current)} selected"

    with st.popover(summary, use_container_width=True):
        st.caption(label)
        sa_col, ca_col = st.columns(2)
        with sa_col:
            if st.button("Select all", key=f"{key}_selall", use_container_width=True):
                st.session_state[persist_key] = list(options)
                st.rerun()
        with ca_col:
            if st.button("Clear all", key=f"{key}_clrall", use_container_width=True):
                st.session_state[persist_key] = []
                st.rerun()
        for opt in options:
            st.checkbox(opt, key=cb_keys[opt], on_change=_sync)

    return st.session_state[persist_key]


def persistent_segmented_control(label, options, state_key, default=None, **kwargs):
    """Wraps st.segmented_control so its value survives being conditionally
    skipped across reruns (e.g. switching away from a tab and back) — the same
    Streamlit widget-lifecycle issue checkbox_multiselect works around above.
    Keeps the real value in st.session_state[state_key] (not the widget's own
    key), fed back in as `default=` every render and kept in sync via on_change."""
    if state_key not in st.session_state or st.session_state[state_key] not in options:
        st.session_state[state_key] = default if default in options else options[0]
    widget_key = f"{state_key}__w"

    def _sync():
        st.session_state[state_key] = st.session_state[widget_key]

    st.segmented_control(label, options, default=st.session_state[state_key], key=widget_key, on_change=_sync, **kwargs)
    return st.session_state[state_key]


def persistent_selectbox(label, options, state_key, default=None, **kwargs):
    """Same fix as persistent_segmented_control, for st.selectbox."""
    if state_key not in st.session_state or st.session_state[state_key] not in options:
        st.session_state[state_key] = default if default in options else options[0]
    widget_key = f"{state_key}__w"

    def _sync():
        st.session_state[state_key] = st.session_state[widget_key]

    idx = options.index(st.session_state[state_key])
    st.selectbox(label, options, index=idx, key=widget_key, on_change=_sync, **kwargs)
    return st.session_state[state_key]


def download_csv_button(df, filename, key):
    """CSV export for any table — the raw numeric DataFrame (Month index, real
    values), not the display-formatted strings, so it's actually usable for
    further analysis in Excel/Sheets rather than just a copy of what's on screen."""
    safe_name = filename.replace(" ", "_").replace("%", "pct")
    st.download_button(
        "⬇️ CSV", df.to_csv().encode("utf-8"), file_name=safe_name,
        mime="text/csv", key=key,
    )


def _outline_expanded_state(table_key):
    exp_key = f"{table_key}__expanded_periods"
    if exp_key not in st.session_state:
        st.session_state[exp_key] = set()
    return exp_key, st.session_state[exp_key]


def _outline_header(disp_columns, label_col_text="Month"):
    # One combined markdown call for the whole header row (label cell + every
    # column header cell) — not split across two st.columns. Splitting a plain
    # (no-widget) row across independent Streamlit column blocks lets Streamlit
    # under-measure one side's wrapper height (it sizes a markdown element off
    # a default single-line estimate, not actual padded/multi-cell content),
    # so the row collapses shorter than its real content and clips/overlaps
    # the row below it — see the identical sub-row issue this mirrors.
    # Column widths/alignment: no manually-approximated flex ratio here anymore —
    # the outlineColumnFix script (see the components.html block near the top of
    # this file) sizes .outline-label-cell / .outline-value-cells to match the
    # real button column and each column's real content width, for every row of
    # the table alike.
    label_cell = f'<div class="outline-cell outline-label-cell">{label_col_text}</div>'
    cells = "".join(f'<div class="outline-cell">{c}</div>' for c in disp_columns)
    st.markdown(
        f'<div class="outline-row outline-header-row">{label_cell}<div class="outline-value-cells">{cells}</div></div>',
        unsafe_allow_html=True,
    )


def render_outline_table(table_key, periods, agg_df, category_list, sub_df_fn, columns, label_map,
                          pct_cols, currency_cols, cmap=None, gradient_cols=None, groups=None,
                          primary_dim_label=None, secondary_dim_label=None, secondary_categories=None,
                          secondary_sub_df_fn=None, tertiary_dim_label=None, tertiary_categories=None,
                          tertiary_sub_df_fn=None, primary_row_suffix="", secondary_row_prefix="", tertiary_row_prefix="",
                          quaternary_dim_label=None, quaternary_categories=None, quaternary_sub_df_fn=None,
                          quaternary_row_prefix=""):
    """Google-Sheets-style row outline. Each period is one row showing the
    combined/aggregate value — exactly as the table looked before any
    per-category breakdown existed. A '+' control expands that period IN PLACE
    into one sub-row per checked category directly beneath it; '-' collapses it
    back; other periods' expand state is independent (kept in
    st.session_state[f"{table_key}__expanded_periods"]).

    Falls back to the original single pandas-Styler heatmap table (no +/-
    control at all — nothing to expand) when there are 0-1 categories, which is
    the common/default case (checkbox_multiselect's own default picks exactly
    one category almost everywhere). groups, if given (raw column-name groups,
    same shape as styled_multi_group_table expects), renders that fallback with
    multiple independent color scales instead of a single cmap/gradient_cols.

    When secondary_categories/secondary_sub_df_fn(l1_cat, l2_cat) are given
    (metrics with 2+ active breakdown dimensions, e.g. Cross Sales —
    acq_business_line x cm_business_line — and Cross Sales (Platform x Acq BL)
    — acq_business_line x cm_business_line x acq_platform), each category_list
    row gets its OWN '+'/'-' to expand a SECOND level of sub-rows beneath it,
    one per secondary category — independent per (period, category) pair, kept
    in st.session_state[f"{table_key}__expanded_L1"]. If tertiary_categories/
    tertiary_sub_df_fn(l1_cat, l2_cat, l3_cat) are ALSO given (3 active
    dimensions), the L2 rows become expandable too (state in
    st.session_state[f"{table_key}__expanded_L2"]), revealing a THIRD level
    beneath an expanded L2 row. primary_dim_label/secondary_dim_label/
    tertiary_dim_label label each level via a one-time caption above the table
    (rather than a per-row prefix) since these dimensions can share the exact
    same underlying category values (e.g. "Group Online" is both an
    Acquisition Business Line and a CM Business Line).

    Returns the currently-VISIBLE flattened DataFrame — collapsed periods
    contribute just their aggregate row, expanded periods contribute their
    aggregate row followed by one row per category (and, for an expanded
    category, one row per secondary category) — for reuse as the CSV export
    (so CSV content always matches what's on screen)."""
    pct_cols = pct_cols or set()
    currency_cols = currency_cols or set()
    has_l2 = bool(secondary_categories) and secondary_sub_df_fn is not None
    has_l3 = has_l2 and bool(tertiary_categories) and tertiary_sub_df_fn is not None
    has_l4 = has_l3 and bool(quaternary_categories) and quaternary_sub_df_fn is not None
    disp_columns = [label_map.get(c, c) for c in columns]

    if len(category_list) <= 1:
        disp = dp.relabel(agg_df.reindex(columns=columns), label_map)
        pct_disp = {label_map.get(c, c) for c in pct_cols}
        currency_disp = {label_map.get(c, c) for c in currency_cols}
        formatted = dp.format_table(disp, pct_disp, currency_disp)
        if groups:
            disp_groups = [([label_map.get(c, c) for c in cols], g_cmap) for cols, g_cmap in groups]
            st.table(dp.styled_multi_group_table(formatted, disp, disp_groups))
        else:
            grad_cols = [label_map.get(c, c) for c in (gradient_cols or columns) if label_map.get(c, c) in disp.columns]
            st.table(dp.styled_cohort_table(formatted, disp, grad_cols, cmap=cmap or dp.BLUE_HEATMAP_CMAP))
        return disp

    exp_key, expanded = _outline_expanded_state(table_key)
    l1_exp_key = f"{table_key}__expanded_L1"
    if l1_exp_key not in st.session_state:
        st.session_state[l1_exp_key] = set()
    l1_expanded = st.session_state[l1_exp_key]
    l2_exp_key = f"{table_key}__expanded_L2"
    if l2_exp_key not in st.session_state:
        st.session_state[l2_exp_key] = set()
    l2_expanded = st.session_state[l2_exp_key]
    l3_exp_key = f"{table_key}__expanded_L3"
    if l3_exp_key not in st.session_state:
        st.session_state[l3_exp_key] = set()
    l3_expanded = st.session_state[l3_exp_key]

    def _fmt(v, c):
        if pd.isna(v):
            return "–"
        if c in pct_cols:
            return f"{v:,.1f}%"
        prefix = "₹" if c in currency_cols else ""
        return f"{prefix}{v:,.0f}"

    with st.container(key=f"outline_{table_key}"):
        ec1, ec2, _sp = st.columns([1.3, 1.3, 6.1])
        with ec1:
            if st.button("Expand all periods", key=f"{table_key}_expand_all"):
                st.session_state[exp_key] = set(periods)
                if has_l2:
                    st.session_state[l1_exp_key] = {(p, cat) for p in periods for cat in category_list}
                if has_l3:
                    st.session_state[l2_exp_key] = {
                        (p, cat, l2_cat) for p in periods for cat in category_list for l2_cat in secondary_categories
                    }
                if has_l4:
                    st.session_state[l3_exp_key] = {
                        (p, cat, l2_cat, l3_cat)
                        for p in periods for cat in category_list
                        for l2_cat in secondary_categories for l3_cat in tertiary_categories
                    }
                st.rerun()
        with ec2:
            if st.button("Collapse all periods", key=f"{table_key}_collapse_all"):
                st.session_state[exp_key] = set()
                if has_l2:
                    st.session_state[l1_exp_key] = set()
                if has_l3:
                    st.session_state[l2_exp_key] = set()
                if has_l4:
                    st.session_state[l3_exp_key] = set()
                st.rerun()

        if has_l2:
            # One-time explanation of the hierarchy, rather than repeating the
            # full dimension name on every single row (which wraps a real
            # st.button across many lines in its narrow column — see the
            # l1_label_text comment below). Sub-rows are still prefixed in
            # their CSV export key, so between this caption and that prefix
            # it's always clear which dimension a given row's value belongs to.
            levels = [primary_dim_label, secondary_dim_label]
            if has_l3:
                levels.append(tertiary_dim_label)
            if has_l4:
                levels.append(quaternary_dim_label)
            st.caption(f"Rows expand: {' → '.join(levels)}")

        st.markdown('<div class="outline-wrap">', unsafe_allow_html=True)
        _outline_header(disp_columns)

        visible_rows = {}
        for p in periods:
            is_exp = p in expanded
            label = p.strftime("%b-%Y")
            agg_row = agg_df.loc[p] if p in agg_df.index else pd.Series({c: np.nan for c in columns})
            lcol, rcol = st.columns([1.3, 8.7])
            with lcol:
                # icon=, not a leading "+"/"-" character embedded in the label
                # text — st.button renders its label as Markdown, where a
                # leading "+" is CommonMark bullet-list syntax and silently
                # vanishes instead of displaying (the existing format_table
                # docstring already flags the analogous "-" bullet issue).
                if st.button(label, key=f"{table_key}_{label}_toggle", icon="➖" if is_exp else "➕"):
                    if is_exp:
                        expanded.discard(p)
                    else:
                        expanded.add(p)
                    st.session_state[exp_key] = expanded
                    st.rerun()
            with rcol:
                cells = "".join(f'<div class="outline-cell">{_fmt(agg_row.get(c), c)}</div>' for c in columns)
                st.markdown(
                    f'<div class="outline-row outline-agg-row"><div class="outline-value-cells">{cells}</div></div>',
                    unsafe_allow_html=True,
                )
            visible_rows[label] = {c: agg_row.get(c, np.nan) for c in columns}

            if is_exp and not has_l2:
                # All of this period's sub-rows are built as ONE combined HTML
                # string / single st.markdown call, not one call per category.
                # Streamlit sizes a *freshly-added* markdown element's wrapper
                # off a stale/estimated height until a later layout pass
                # corrects it — with one call per row that showed up as newly
                # expanded rows visually overlapping each other; a single call
                # only pays that estimation cost once, for the whole block.
                sub_rows_html = []
                for cat in category_list:
                    sub_df = sub_df_fn(cat)
                    sub_row = sub_df.loc[p] if (sub_df is not None and p in sub_df.index) else pd.Series({c: np.nan for c in columns})
                    label_cell = f'<div class="outline-cell outline-label-cell">&nbsp;&nbsp;&nbsp;{cat}{primary_row_suffix}</div>'
                    value_cells = "".join(f'<div class="outline-cell">{_fmt(sub_row.get(c), c)}</div>' for c in columns)
                    sub_rows_html.append(
                        f'<div class="outline-row outline-sub-row">{label_cell}<div class="outline-value-cells">{value_cells}</div></div>'
                    )
                    visible_rows[f"{label} — {cat}"] = {c: sub_row.get(c, np.nan) for c in columns}
                st.markdown("".join(sub_rows_html), unsafe_allow_html=True)

            elif is_exp and has_l2:
                # Two-level outline (Cross Sales / Cross Sales (Platform x Acq
                # BL)): each L1 category (e.g. an Acquisition Business Line) is
                # its OWN expandable row — a real button, same as a period row,
                # just one level in — so it needs its own st.columns split
                # rather than the batched-markdown treatment above (a real
                # widget can't be part of one concatenated markdown string).
                # primary_dim_label/secondary_dim_label prefix every row so
                # it's never ambiguous which dimension a value belongs to when
                # both dimensions share the same underlying category names
                # (e.g. "Group Online" exists as both an Acq BL and a CM BL).
                for cat in category_list:
                    sub_df = sub_df_fn(cat)
                    sub_row = sub_df.loc[p] if (sub_df is not None and p in sub_df.index) else pd.Series({c: np.nan for c in columns})
                    l1_key = (p, cat)
                    l1_is_exp = l1_key in l1_expanded
                    # The BUTTON label stays just the category name, unprefixed
                    # — this real st.button lives in the same narrow ~9% column
                    # as a period button, and a long "Acquisition Business
                    # Line: ..." prefix wrapped it across 6-8 lines, breaking
                    # the row height entirely. Which dimension L1 is comes from
                    # the one-time caption above the table instead; l1_label_text
                    # (with the full prefix) is still used for the CSV export
                    # key, where there's no width constraint.
                    l1lcol, l1rcol = st.columns([1.3, 8.7])
                    with l1lcol:
                        if st.button(
                            f"{cat}{primary_row_suffix}", key=f"{table_key}_{label}_{cat}_l1_toggle",
                            icon="➖" if l1_is_exp else "➕",
                        ):
                            if l1_is_exp:
                                l1_expanded.discard(l1_key)
                            else:
                                l1_expanded.add(l1_key)
                            st.session_state[l1_exp_key] = l1_expanded
                            st.rerun()
                    with l1rcol:
                        value_cells = "".join(f'<div class="outline-cell">{_fmt(sub_row.get(c), c)}</div>' for c in columns)
                        st.markdown(
                            f'<div class="outline-row outline-sub-row"><div class="outline-value-cells">{value_cells}</div></div>',
                            unsafe_allow_html=True,
                        )
                    l1_label_text = f"{primary_dim_label + ': ' if primary_dim_label else ''}{cat}"  # CSV export key only — no column-width constraint there
                    visible_rows[f"{label} — {l1_label_text}"] = {c: sub_row.get(c, np.nan) for c in columns}

                    if l1_is_exp and not has_l3:
                        # 2-level case (e.g. Cross Sales): L2 stays plain
                        # batched markdown, exactly as before.
                        l2_rows_html = []
                        for l2_cat in secondary_categories:
                            l2_df = secondary_sub_df_fn(cat, l2_cat)
                            l2_row = l2_df.loc[p] if (l2_df is not None and p in l2_df.index) else pd.Series({c: np.nan for c in columns})
                            # On-screen label gets a short prefix/suffix (e.g.
                            # "CM " / " Acq") when the caller identifies this as
                            # acq_business_line/cm_business_line specifically —
                            # they share the same underlying category names, so
                            # this disambiguates every row, not just via the
                            # one-time caption above the table. l2_label_text
                            # (with the full dimension-name prefix) is still
                            # used for the CSV export key.
                            label_cell = f'<div class="outline-cell outline-label-cell">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{secondary_row_prefix}{l2_cat}</div>'
                            l2_value_cells = "".join(f'<div class="outline-cell">{_fmt(l2_row.get(c), c)}</div>' for c in columns)
                            l2_rows_html.append(
                                f'<div class="outline-row outline-sub-row outline-sub-row-l2">{label_cell}<div class="outline-value-cells">{l2_value_cells}</div></div>'
                            )
                            l2_label_text = f"{secondary_dim_label + ': ' if secondary_dim_label else ''}{l2_cat}"
                            visible_rows[f"{label} — {l1_label_text} — {l2_label_text}"] = {c: l2_row.get(c, np.nan) for c in columns}
                        st.markdown("".join(l2_rows_html), unsafe_allow_html=True)

                    elif l1_is_exp and has_l3:
                        # 3-level case (Cross Sales (Platform x Acq BL), now that
                        # cm_business_line has real per-type values): L2 becomes
                        # its OWN expandable row too (same real-button treatment
                        # as L1 above), revealing L3 as the new batched-markdown
                        # leaf level beneath an expanded L2 row.
                        for l2_cat in secondary_categories:
                            l2_df = secondary_sub_df_fn(cat, l2_cat)
                            l2_row = l2_df.loc[p] if (l2_df is not None and p in l2_df.index) else pd.Series({c: np.nan for c in columns})
                            l2_key = (p, cat, l2_cat)
                            l2_is_exp = l2_key in l2_expanded
                            l2lcol, l2rcol = st.columns([1.3, 8.7])
                            with l2lcol:
                                if st.button(
                                    f"{secondary_row_prefix}{l2_cat}", key=f"{table_key}_{label}_{cat}_{l2_cat}_l2_toggle",
                                    icon="➖" if l2_is_exp else "➕",
                                ):
                                    if l2_is_exp:
                                        l2_expanded.discard(l2_key)
                                    else:
                                        l2_expanded.add(l2_key)
                                    st.session_state[l2_exp_key] = l2_expanded
                                    st.rerun()
                            with l2rcol:
                                l2_value_cells = "".join(f'<div class="outline-cell">{_fmt(l2_row.get(c), c)}</div>' for c in columns)
                                st.markdown(
                                    f'<div class="outline-row outline-sub-row outline-sub-row-l2"><div class="outline-value-cells">{l2_value_cells}</div></div>',
                                    unsafe_allow_html=True,
                                )
                            l2_label_text = f"{secondary_dim_label + ': ' if secondary_dim_label else ''}{l2_cat}"  # CSV export key only
                            visible_rows[f"{label} — {l1_label_text} — {l2_label_text}"] = {c: l2_row.get(c, np.nan) for c in columns}

                            if l2_is_exp and not has_l4:
                                l3_rows_html = []
                                for l3_cat in tertiary_categories:
                                    l3_df = tertiary_sub_df_fn(cat, l2_cat, l3_cat)
                                    l3_row = l3_df.loc[p] if (l3_df is not None and p in l3_df.index) else pd.Series({c: np.nan for c in columns})
                                    label_cell = f'<div class="outline-cell outline-label-cell">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{tertiary_row_prefix}{l3_cat}</div>'
                                    l3_value_cells = "".join(f'<div class="outline-cell">{_fmt(l3_row.get(c), c)}</div>' for c in columns)
                                    l3_rows_html.append(
                                        f'<div class="outline-row outline-sub-row outline-sub-row-l3">{label_cell}<div class="outline-value-cells">{l3_value_cells}</div></div>'
                                    )
                                    l3_label_text = f"{tertiary_dim_label + ': ' if tertiary_dim_label else ''}{l3_cat}"
                                    visible_rows[f"{label} — {l1_label_text} — {l2_label_text} — {l3_label_text}"] = {c: l3_row.get(c, np.nan) for c in columns}
                                st.markdown("".join(l3_rows_html), unsafe_allow_html=True)

                            elif l2_is_exp and has_l4:
                                # 4-level case (Cross Sales (Platform x Acq BL),
                                # now that platform/"CM Platform" also has real
                                # per-type values): L3 becomes its OWN expandable
                                # row too (same real-button treatment as L1/L2
                                # above), revealing L4 as the new batched-markdown
                                # leaf level beneath an expanded L3 row.
                                for l3_cat in tertiary_categories:
                                    l3_df = tertiary_sub_df_fn(cat, l2_cat, l3_cat)
                                    l3_row = l3_df.loc[p] if (l3_df is not None and p in l3_df.index) else pd.Series({c: np.nan for c in columns})
                                    l3_key = (p, cat, l2_cat, l3_cat)
                                    l3_is_exp = l3_key in l3_expanded
                                    l3lcol, l3rcol = st.columns([1.3, 8.7])
                                    with l3lcol:
                                        if st.button(
                                            f"{tertiary_row_prefix}{l3_cat}", key=f"{table_key}_{label}_{cat}_{l2_cat}_{l3_cat}_l3_toggle",
                                            icon="➖" if l3_is_exp else "➕",
                                        ):
                                            if l3_is_exp:
                                                l3_expanded.discard(l3_key)
                                            else:
                                                l3_expanded.add(l3_key)
                                            st.session_state[l3_exp_key] = l3_expanded
                                            st.rerun()
                                    with l3rcol:
                                        l3_value_cells = "".join(f'<div class="outline-cell">{_fmt(l3_row.get(c), c)}</div>' for c in columns)
                                        st.markdown(
                                            f'<div class="outline-row outline-sub-row outline-sub-row-l3"><div class="outline-value-cells">{l3_value_cells}</div></div>',
                                            unsafe_allow_html=True,
                                        )
                                    l3_label_text = f"{tertiary_dim_label + ': ' if tertiary_dim_label else ''}{l3_cat}"  # CSV export key only
                                    visible_rows[f"{label} — {l1_label_text} — {l2_label_text} — {l3_label_text}"] = {c: l3_row.get(c, np.nan) for c in columns}

                                    if l3_is_exp:
                                        l4_rows_html = []
                                        for l4_cat in quaternary_categories:
                                            l4_df = quaternary_sub_df_fn(cat, l2_cat, l3_cat, l4_cat)
                                            l4_row = l4_df.loc[p] if (l4_df is not None and p in l4_df.index) else pd.Series({c: np.nan for c in columns})
                                            label_cell = f'<div class="outline-cell outline-label-cell">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{quaternary_row_prefix}{l4_cat}</div>'
                                            l4_value_cells = "".join(f'<div class="outline-cell">{_fmt(l4_row.get(c), c)}</div>' for c in columns)
                                            l4_rows_html.append(
                                                f'<div class="outline-row outline-sub-row outline-sub-row-l4">{label_cell}<div class="outline-value-cells">{l4_value_cells}</div></div>'
                                            )
                                            l4_label_text = f"{quaternary_dim_label + ': ' if quaternary_dim_label else ''}{l4_cat}"
                                            visible_rows[f"{label} — {l1_label_text} — {l2_label_text} — {l3_label_text} — {l4_label_text}"] = {c: l4_row.get(c, np.nan) for c in columns}
                                        st.markdown("".join(l4_rows_html), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    visible_df = pd.DataFrame.from_dict(visible_rows, orient="index", columns=columns)
    visible_df.index.name = "Month"
    visible_df = visible_df.rename(columns=label_map)
    return visible_df


def render_outline_diff_table(table_key, periods, agg_df, category_list, sub_df_fn, columns, label_map,
                               pct_cols=None, currency_cols=None, emphasize_cols=None, title="",
                               chart_mode="trend", chart_col=None, chart_y_title="",
                               primary_dim_label=None, secondary_dim_label=None, secondary_categories=None,
                               secondary_sub_df_fn=None, tertiary_dim_label=None, tertiary_categories=None,
                               tertiary_sub_df_fn=None, primary_row_suffix="", secondary_row_prefix="", tertiary_row_prefix="",
                               quaternary_dim_label=None, quaternary_categories=None, quaternary_sub_df_fn=None,
                               quaternary_row_prefix=""):
    """Period-over-period change, using the exact same per-period +/- outline
    mechanism as render_outline_table above — and, deliberately, the SAME
    st.session_state expanded-periods key (table_key), so expanding a period in
    either this table or its corresponding main table expands it in both.

    Absolute-value columns get an Absolute Diff / % Diff toggle (default % Diff);
    columns already in pct_cols always show a percentage-point (pp) diff. Growth
    is green, drop is red; emphasize_cols (e.g. 'Total') get a bold left border
    so the aggregate column reads as distinct from individual category columns."""
    pct_cols = pct_cols or set()
    currency_cols = currency_cols or set()
    emphasize_cols = emphasize_cols or []
    if len(periods) < 2:
        return

    st.markdown(f"###### {title} — Period-over-Period Change")

    all_cols = set(columns)
    all_pct = bool(all_cols) and all_cols <= pct_cols
    if not all_pct:
        diff_mode = persistent_segmented_control(
            "Diff mode", ["Absolute Diff", "% Diff"], state_key=f"{table_key}_diffmode", default="% Diff",
            label_visibility="collapsed",
            help="Absolute Diff = current period minus previous. % Diff = growth/drop vs. the previous period.",
        )
    else:
        diff_mode = "% Diff"  # irrelevant — every column here is pct_cols and always shows a pp diff

    diff_agg, kinds = dp.compute_period_diff(agg_df.reindex(columns=columns), pct_cols, diff_mode)
    if diff_agg.empty:
        return
    diff_periods = list(diff_agg.index)

    def _diff_sub(cat):
        sub = sub_df_fn(cat)
        if sub is None or sub.empty:
            return None
        d, _ = dp.compute_period_diff(sub.reindex(columns=columns), pct_cols, diff_mode)
        return d

    has_l2 = bool(secondary_categories) and secondary_sub_df_fn is not None
    has_l3 = has_l2 and bool(tertiary_categories) and tertiary_sub_df_fn is not None
    has_l4 = has_l3 and bool(quaternary_categories) and quaternary_sub_df_fn is not None

    def _diff_sub_l2(l1_cat, l2_cat):
        sub = secondary_sub_df_fn(l1_cat, l2_cat)
        if sub is None or sub.empty:
            return None
        d, _ = dp.compute_period_diff(sub.reindex(columns=columns), pct_cols, diff_mode)
        return d

    def _diff_sub_l3(l1_cat, l2_cat, l3_cat):
        sub = tertiary_sub_df_fn(l1_cat, l2_cat, l3_cat)
        if sub is None or sub.empty:
            return None
        d, _ = dp.compute_period_diff(sub.reindex(columns=columns), pct_cols, diff_mode)
        return d

    def _diff_sub_l4(l1_cat, l2_cat, l3_cat, l4_cat):
        sub = quaternary_sub_df_fn(l1_cat, l2_cat, l3_cat, l4_cat)
        if sub is None or sub.empty:
            return None
        d, _ = dp.compute_period_diff(sub.reindex(columns=columns), pct_cols, diff_mode)
        return d

    exp_key, expanded = _outline_expanded_state(table_key)  # shared with the main table above
    l1_exp_key = f"{table_key}__expanded_L1"  # shared with the main table above
    if l1_exp_key not in st.session_state:
        st.session_state[l1_exp_key] = set()
    l1_expanded = st.session_state[l1_exp_key]
    l2_exp_key = f"{table_key}__expanded_L2"  # shared with the main table above
    if l2_exp_key not in st.session_state:
        st.session_state[l2_exp_key] = set()
    l2_expanded = st.session_state[l2_exp_key]
    l3_exp_key = f"{table_key}__expanded_L3"  # shared with the main table above
    if l3_exp_key not in st.session_state:
        st.session_state[l3_exp_key] = set()
    l3_expanded = st.session_state[l3_exp_key]
    disp_columns = [label_map.get(c, c) for c in columns]
    has_children = len(category_list) > 1

    def _fmt(v, c):
        if pd.isna(v):
            return "–"
        kind = kinds.get(c, "abs")
        sign = "+" if v > 0 else ("-" if v < 0 else "")
        mag = abs(v)
        if kind == "pp":
            return f"{sign}{mag:,.1f} pp"
        if kind == "pct":
            return f"{sign}{mag:,.1f}%"
        prefix = "₹" if c in currency_cols else ""
        return f"{sign}{prefix}{mag:,.0f}"

    def _cls(v, c):
        cls = "outline-emphasize" if c in emphasize_cols else ""
        if pd.isna(v):
            return cls
        if v > 0:
            return f"{cls} outline-diff-pos".strip()
        if v < 0:
            return f"{cls} outline-diff-neg".strip()
        return cls

    with st.container(key=f"outline_{table_key}_diff"):
        st.markdown('<div class="outline-wrap">', unsafe_allow_html=True)
        _outline_header(disp_columns)

        visible_rows = {}
        chart_series = []

        if not has_children:
            # No expand controls anywhere in this diff table (0-1 categories —
            # e.g. Recency, or any diff table whose main table has nothing to
            # expand either) — every row is plain HTML with no widget, so ALL
            # of them are batched into ONE combined st.markdown call. Even a
            # single plain row's own wrapper can still get sized off
            # Streamlit's default single-line estimate rather than its real
            # (taller, padded) content; batching sidesteps relying on any one
            # row's individual measurement being correct.
            rows_html = []
            for p in diff_periods:
                label = p.strftime("%b-%Y")
                row = diff_agg.loc[p]
                cells = "".join(f'<div class="outline-cell {_cls(row.get(c), c)}">{_fmt(row.get(c), c)}</div>' for c in columns)
                label_cell = f'<div class="outline-cell outline-label-cell">{label}</div>'
                rows_html.append(
                    f'<div class="outline-row outline-agg-row">{label_cell}<div class="outline-value-cells">{cells}</div></div>'
                )
                visible_rows[label] = {c: row.get(c, np.nan) for c in columns}
                if chart_col:
                    chart_series.append(row.get(chart_col, np.nan))
            st.markdown("".join(rows_html), unsafe_allow_html=True)
            diff_periods_for_loop = []  # already fully rendered above
        else:
            diff_periods_for_loop = diff_periods

        for p in diff_periods_for_loop:
            label = p.strftime("%b-%Y")
            row = diff_agg.loc[p]
            is_exp = p in expanded
            cells = "".join(f'<div class="outline-cell {_cls(row.get(c), c)}">{_fmt(row.get(c), c)}</div>' for c in columns)
            # A real st.button (a widget, not raw HTML) anchors this row's true
            # height correctly, so splitting button | values across two
            # st.columns is safe here (unlike the plain, no-widget rows above).
            lcol, rcol = st.columns([1.3, 8.7])
            with lcol:
                if st.button(label, key=f"{table_key}_diff_{label}_toggle", icon="➖" if is_exp else "➕"):
                    if is_exp:
                        expanded.discard(p)
                    else:
                        expanded.add(p)
                    st.session_state[exp_key] = expanded
                    st.rerun()
            with rcol:
                st.markdown(
                    f'<div class="outline-row outline-agg-row"><div class="outline-value-cells">{cells}</div></div>',
                    unsafe_allow_html=True,
                )
            visible_rows[label] = {c: row.get(c, np.nan) for c in columns}
            if chart_col:
                chart_series.append(row.get(chart_col, np.nan))

            if is_exp and not has_l2:
                # Single combined st.markdown call for all of this period's
                # sub-rows — see the matching comment in render_outline_table
                # for why one call per row visually overlapped.
                sub_rows_html = []
                for cat in category_list:
                    d = _diff_sub(cat)
                    sub_row = d.loc[p] if (d is not None and p in d.index) else pd.Series({c: np.nan for c in columns})
                    label_cell = f'<div class="outline-cell outline-label-cell">&nbsp;&nbsp;&nbsp;{cat}{primary_row_suffix}</div>'
                    value_cells = "".join(
                        f'<div class="outline-cell {_cls(sub_row.get(c), c)}">{_fmt(sub_row.get(c), c)}</div>'
                        for c in columns
                    )
                    sub_rows_html.append(
                        f'<div class="outline-row outline-sub-row">{label_cell}<div class="outline-value-cells">{value_cells}</div></div>'
                    )
                    visible_rows[f"{label} — {cat}"] = {c: sub_row.get(c, np.nan) for c in columns}
                st.markdown("".join(sub_rows_html), unsafe_allow_html=True)

            elif is_exp and has_l2:
                # Two-level outline, mirroring render_outline_table above —
                # same shared l1_exp_key, so a category expanded in the main
                # table (or vice versa) is already expanded here too.
                for cat in category_list:
                    d = _diff_sub(cat)
                    sub_row = d.loc[p] if (d is not None and p in d.index) else pd.Series({c: np.nan for c in columns})
                    l1_key = (p, cat)
                    l1_is_exp = l1_key in l1_expanded
                    l1lcol, l1rcol = st.columns([1.3, 8.7])
                    with l1lcol:
                        if st.button(
                            f"{cat}{primary_row_suffix}", key=f"{table_key}_diff_{label}_{cat}_l1_toggle",
                            icon="➖" if l1_is_exp else "➕",
                        ):
                            if l1_is_exp:
                                l1_expanded.discard(l1_key)
                            else:
                                l1_expanded.add(l1_key)
                            st.session_state[l1_exp_key] = l1_expanded
                            st.rerun()
                    with l1rcol:
                        value_cells = "".join(
                            f'<div class="outline-cell {_cls(sub_row.get(c), c)}">{_fmt(sub_row.get(c), c)}</div>'
                            for c in columns
                        )
                        st.markdown(
                            f'<div class="outline-row outline-sub-row"><div class="outline-value-cells">{value_cells}</div></div>',
                            unsafe_allow_html=True,
                        )
                    l1_label_text = f"{primary_dim_label + ': ' if primary_dim_label else ''}{cat}"  # CSV export key only
                    visible_rows[f"{label} — {l1_label_text}"] = {c: sub_row.get(c, np.nan) for c in columns}

                    if l1_is_exp and not has_l3:
                        l2_rows_html = []
                        for l2_cat in secondary_categories:
                            d2 = _diff_sub_l2(cat, l2_cat)
                            l2_row = d2.loc[p] if (d2 is not None and p in d2.index) else pd.Series({c: np.nan for c in columns})
                            label_cell = f'<div class="outline-cell outline-label-cell">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{secondary_row_prefix}{l2_cat}</div>'
                            l2_value_cells = "".join(
                                f'<div class="outline-cell {_cls(l2_row.get(c), c)}">{_fmt(l2_row.get(c), c)}</div>'
                                for c in columns
                            )
                            l2_rows_html.append(
                                f'<div class="outline-row outline-sub-row outline-sub-row-l2">{label_cell}<div class="outline-value-cells">{l2_value_cells}</div></div>'
                            )
                            l2_label_text = f"{secondary_dim_label + ': ' if secondary_dim_label else ''}{l2_cat}"
                            visible_rows[f"{label} — {l1_label_text} — {l2_label_text}"] = {c: l2_row.get(c, np.nan) for c in columns}
                        st.markdown("".join(l2_rows_html), unsafe_allow_html=True)

                    elif l1_is_exp and has_l3:
                        # 3-level diff, mirroring render_outline_table's 3-level
                        # branch — same shared l2_exp_key.
                        for l2_cat in secondary_categories:
                            d2 = _diff_sub_l2(cat, l2_cat)
                            l2_row = d2.loc[p] if (d2 is not None and p in d2.index) else pd.Series({c: np.nan for c in columns})
                            l2_key = (p, cat, l2_cat)
                            l2_is_exp = l2_key in l2_expanded
                            l2lcol, l2rcol = st.columns([1.3, 8.7])
                            with l2lcol:
                                if st.button(
                                    f"{secondary_row_prefix}{l2_cat}", key=f"{table_key}_diff_{label}_{cat}_{l2_cat}_l2_toggle",
                                    icon="➖" if l2_is_exp else "➕",
                                ):
                                    if l2_is_exp:
                                        l2_expanded.discard(l2_key)
                                    else:
                                        l2_expanded.add(l2_key)
                                    st.session_state[l2_exp_key] = l2_expanded
                                    st.rerun()
                            with l2rcol:
                                l2_value_cells = "".join(
                                    f'<div class="outline-cell {_cls(l2_row.get(c), c)}">{_fmt(l2_row.get(c), c)}</div>'
                                    for c in columns
                                )
                                st.markdown(
                                    f'<div class="outline-row outline-sub-row outline-sub-row-l2"><div class="outline-value-cells">{l2_value_cells}</div></div>',
                                    unsafe_allow_html=True,
                                )
                            l2_label_text = f"{secondary_dim_label + ': ' if secondary_dim_label else ''}{l2_cat}"  # CSV export key only
                            visible_rows[f"{label} — {l1_label_text} — {l2_label_text}"] = {c: l2_row.get(c, np.nan) for c in columns}

                            if l2_is_exp and not has_l4:
                                l3_rows_html = []
                                for l3_cat in tertiary_categories:
                                    d3 = _diff_sub_l3(cat, l2_cat, l3_cat)
                                    l3_row = d3.loc[p] if (d3 is not None and p in d3.index) else pd.Series({c: np.nan for c in columns})
                                    label_cell = f'<div class="outline-cell outline-label-cell">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{tertiary_row_prefix}{l3_cat}</div>'
                                    l3_value_cells = "".join(
                                        f'<div class="outline-cell {_cls(l3_row.get(c), c)}">{_fmt(l3_row.get(c), c)}</div>'
                                        for c in columns
                                    )
                                    l3_rows_html.append(
                                        f'<div class="outline-row outline-sub-row outline-sub-row-l3">{label_cell}<div class="outline-value-cells">{l3_value_cells}</div></div>'
                                    )
                                    l3_label_text = f"{tertiary_dim_label + ': ' if tertiary_dim_label else ''}{l3_cat}"
                                    visible_rows[f"{label} — {l1_label_text} — {l2_label_text} — {l3_label_text}"] = {c: l3_row.get(c, np.nan) for c in columns}
                                st.markdown("".join(l3_rows_html), unsafe_allow_html=True)

                            elif l2_is_exp and has_l4:
                                # 4-level diff, mirroring render_outline_table's
                                # 4-level branch — same shared l3_exp_key.
                                for l3_cat in tertiary_categories:
                                    d3 = _diff_sub_l3(cat, l2_cat, l3_cat)
                                    l3_row = d3.loc[p] if (d3 is not None and p in d3.index) else pd.Series({c: np.nan for c in columns})
                                    l3_key = (p, cat, l2_cat, l3_cat)
                                    l3_is_exp = l3_key in l3_expanded
                                    l3lcol, l3rcol = st.columns([1.3, 8.7])
                                    with l3lcol:
                                        if st.button(
                                            f"{tertiary_row_prefix}{l3_cat}", key=f"{table_key}_diff_{label}_{cat}_{l2_cat}_{l3_cat}_l3_toggle",
                                            icon="➖" if l3_is_exp else "➕",
                                        ):
                                            if l3_is_exp:
                                                l3_expanded.discard(l3_key)
                                            else:
                                                l3_expanded.add(l3_key)
                                            st.session_state[l3_exp_key] = l3_expanded
                                            st.rerun()
                                    with l3rcol:
                                        l3_value_cells = "".join(
                                            f'<div class="outline-cell {_cls(l3_row.get(c), c)}">{_fmt(l3_row.get(c), c)}</div>'
                                            for c in columns
                                        )
                                        st.markdown(
                                            f'<div class="outline-row outline-sub-row outline-sub-row-l3"><div class="outline-value-cells">{l3_value_cells}</div></div>',
                                            unsafe_allow_html=True,
                                        )
                                    l3_label_text = f"{tertiary_dim_label + ': ' if tertiary_dim_label else ''}{l3_cat}"  # CSV export key only
                                    visible_rows[f"{label} — {l1_label_text} — {l2_label_text} — {l3_label_text}"] = {c: l3_row.get(c, np.nan) for c in columns}

                                    if l3_is_exp:
                                        l4_rows_html = []
                                        for l4_cat in quaternary_categories:
                                            d4 = _diff_sub_l4(cat, l2_cat, l3_cat, l4_cat)
                                            l4_row = d4.loc[p] if (d4 is not None and p in d4.index) else pd.Series({c: np.nan for c in columns})
                                            label_cell = f'<div class="outline-cell outline-label-cell">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{quaternary_row_prefix}{l4_cat}</div>'
                                            l4_value_cells = "".join(
                                                f'<div class="outline-cell {_cls(l4_row.get(c), c)}">{_fmt(l4_row.get(c), c)}</div>'
                                                for c in columns
                                            )
                                            l4_rows_html.append(
                                                f'<div class="outline-row outline-sub-row outline-sub-row-l4">{label_cell}<div class="outline-value-cells">{l4_value_cells}</div></div>'
                                            )
                                            l4_label_text = f"{quaternary_dim_label + ': ' if quaternary_dim_label else ''}{l4_cat}"
                                            visible_rows[f"{label} — {l1_label_text} — {l2_label_text} — {l3_label_text} — {l4_label_text}"] = {c: l4_row.get(c, np.nan) for c in columns}
                                        st.markdown("".join(l4_rows_html), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    visible_df = pd.DataFrame.from_dict(visible_rows, orient="index", columns=columns)
    visible_df.index.name = "Month"
    visible_df = visible_df.rename(columns=label_map)
    download_csv_button(visible_df, f"{table_key}_diff.csv", key=f"dl_{table_key}_diff")

    if chart_mode == "trend" and chart_col is not None:
        series = pd.Series(chart_series, index=diff_periods)
        st.plotly_chart(
            ch.single_bar(
                [p.strftime("%b-%Y") for p in diff_periods], series.fillna(0),
                f"{label_map.get(chart_col, chart_col)} Growth/Drop by Month — {title}",
                y_title=chart_y_title, color=dp.diff_bar_colors(series),
            ),
            use_container_width=True,
        )
    elif chart_mode == "latest_by_category":
        cat_cols = [c for c in columns if c not in emphasize_cols]
        if len(cat_cols) >= 2:
            latest = diff_agg[cat_cols].iloc[-1]
            latest_period = diff_periods[-1].strftime("%b-%Y")
            cat_labels = [label_map.get(c, c) for c in cat_cols]
            st.plotly_chart(
                ch.single_bar(
                    cat_labels, latest.fillna(0),
                    f"Latest Period ({latest_period}) Growth/Drop by Category — {title}",
                    y_title=chart_y_title, color=dp.diff_bar_colors(latest),
                ),
                use_container_width=True,
            )


# Auto-refresh the browser tab periodically so the daily 10:00 AM cache-bust
# (see data_loader._daily_cache_bucket) actually gets picked up without a manual click.
st.markdown('<meta http-equiv="refresh" content="600">', unsafe_allow_html=True)

header_l, header_r = st.columns([4, 1])
with header_l:
    st.markdown("## \U0001F4C8 LTV & Repeat Rate Dashboard")
with header_r:
    refresh_clicked = st.button("\U0001F504 Refresh data", use_container_width=True, type="primary")

repeat_raw, ltv_raw, fetched_at = dl.get_data(force_refresh=refresh_clicked)
if refresh_clicked:
    st.toast("Data refreshed from Google Sheets", icon="✅")

repeat_df = dp.build_repeat_df(repeat_raw)
ltv_df = dp.build_ltv_df(ltv_raw)

src_updated = pd.to_datetime(repeat_df["last_updated"], format="%d/%m/%Y %H:%M:%S", errors="coerce").max()
next_refresh = dl.next_refresh_time()
st.caption(
    f"Data as of **{fetched_at.strftime('%d %b %Y, %I:%M %p')}** &nbsp;|&nbsp; "
    f"Source sheet updated **{src_updated.strftime('%d %b %Y, %I:%M %p') if pd.notna(src_updated) else 'unknown'}** &nbsp;|&nbsp; "
    f"Auto-refreshes daily at 10:00 AM (next: {next_refresh.strftime('%d %b, %I:%M %p')})"
)

# ---------------------------------------------------------------- Tabs row ---
COHORT_TABS = {"Revenue", "Users", "Purchases", "AOV", "ARPU"}
PERIOD_METRIC_TABS = {
    "Session Month": {
        "Overall": "Session_Month_Rev",
        "Business Line": "Session_Month_Bussine_linewise",
        "Platform": "Session_Month_platform_Rev",
        "Business Line & Platform": "Session_Month_Bussine_line_platform_wise",
        "BL Contribution to Platform": "Session_Month_Bussine_line_platform_wise",
        "Platform Contribution to BL": "Session_Month_Bussine_line_platform_wise",
    },
    "Purchase Month": {
        "Overall": "Purchase_Month_Rev",
        "Business Line": "Purchase_Month_Bussine_linewise",
        "Platform": "Purchase_Month_platform_Rev",
        "Business Line & Platform": "Purchase_Month_Bussine_line_platform_wise",
        "BL Contribution to Platform": "Purchase_Month_Bussine_line_platform_wise",
        "Platform Contribution to BL": "Purchase_Month_Bussine_line_platform_wise",
    },
}
PERIOD_METRIC_VIEWS = [
    "Overall", "Business Line", "Platform", "Business Line & Platform",
    "BL Contribution to Platform", "Platform Contribution to BL",
]
# The 2 "contribution" views both read the same Business-Line x Platform metric as
# "Business Line & Platform" — they just fix one dimension (via a single-select,
# 'All' meaning "don't fix it — show contribution to the overall total") and break
# down by the other, instead of filtering both to a multi-select.
CONTRIBUTION_VIEWS = {"BL Contribution to Platform", "Platform Contribution to BL"}
TAB_NAMES = ["LTV", "Revenue", "Users", "Purchases", "AOV", "ARPU", "Recency", "Session Month", "Purchase Month"]
with st.container(key="tab_nav"):
    active_tab = st.segmented_control(
        "Section", TAB_NAMES, default="Revenue", key="active_tab", label_visibility="collapsed"
    )
if active_tab is None:
    active_tab = "Revenue"

# --------------------------------------------------------- Month range setup ---
# Computed up front (rather than after the tab-specific filters, as before) so
# every tab can render this one popover inline in its own filter row, instead of
# a separate shared row underneath.
all_periods = sorted(set(repeat_df["period"].dropna().unique()) | set(ltv_df["Month"].dropna().unique()))
period_labels = [pd.Timestamp(p).strftime("%b-%Y") for p in all_periods]
label_to_ts = dict(zip(period_labels, all_periods))
max_idx = len(period_labels) - 1

# Default = the current calendar month (per today's date) plus the 6 months
# before it. Falls back to the latest available month if today's own month isn't
# in the sheet yet (or the sheet runs ahead with forward-looking rows).
_today_month = pd.Timestamp.now().normalize().replace(day=1)
_current_or_earlier = [i for i, p in enumerate(all_periods) if p <= _today_month]
default_to_idx = _current_or_earlier[-1] if _current_or_earlier else max_idx
default_from_idx = max(0, default_to_idx - 6)

QUICK_MONTH_RANGES = [("Last 3 Months", 3), ("Last 6 Months", 6), ("Last 12 Months", 12), ("All", None)]


def render_month_range(container):
    """One popover: 'Last N Months' quick presets (N months before the current
    one, plus the current one) alongside manual From/To selects for anything
    else — replaces 2 separate selectbox columns with a single compact button."""
    if "from_month" not in st.session_state:
        st.session_state["from_month"] = period_labels[default_from_idx]
    if "to_month" not in st.session_state:
        st.session_state["to_month"] = period_labels[default_to_idx]

    with container:
        summary = f"\U0001F4C5 {st.session_state['from_month']} → {st.session_state['to_month']}"
        with st.popover(summary, use_container_width=True):
            st.caption("Quick range")
            quick_cols = st.columns(len(QUICK_MONTH_RANGES))
            for (preset_label, n_months), qcol in zip(QUICK_MONTH_RANGES, quick_cols):
                with qcol:
                    if st.button(preset_label, key=f"qr_{preset_label}", use_container_width=True):
                        from_idx = 0 if n_months is None else max(0, default_to_idx - n_months)
                        st.session_state["from_month"] = period_labels[from_idx]
                        st.session_state["to_month"] = period_labels[default_to_idx]
                        st.rerun()
            st.divider()
            fcol, tcol = st.columns(2)
            with fcol:
                st.selectbox(
                    "From Month", period_labels, key="from_month",
                    help="Start of the acquisition-month range applied to every tab.",
                )
            with tcol:
                st.selectbox(
                    "To Month", period_labels, key="to_month",
                    help="End of the acquisition-month range applied to every tab.",
                )
    a, b = label_to_ts[st.session_state["from_month"]], label_to_ts[st.session_state["to_month"]]
    return (a, b) if a <= b else (b, a)


from_ts, to_ts = None, None  # set exactly once below, inline within each tab's own filter row

# ------------------------------------------------------------- Filters row ---
filtered = pd.DataFrame()
recency_filtered = pd.DataFrame()
period_metric_filtered = pd.DataFrame()
view_mode = "Repeat Rate %"
recency_value_type = "Revenue"
recency_mode = "% of Total"
period_metric_view = "Overall"
period_metric_value_type = "Revenue"
period_metric_component = "Overall"
period_metric_contrib_mode = "% Contrib"
contrib_breakdown_col = None
contrib_fixed_values = []
fixed_options = []
pm_primary_dim = None
pm_primary_values = []
pm_secondary_dim = None
pm_secondary_values = []
pm_base_metric_sub = pd.DataFrame()
cohort_primary_dim = None
cohort_primary_values = []
cohort_secondary_dim = None
cohort_secondary_values = []
cohort_tertiary_dim = None
cohort_tertiary_values = []
cohort_quaternary_dim = None
cohort_quaternary_values = []

if active_tab in COHORT_TABS:
    metric_options = dp.get_metric_options(repeat_df)
    default_metric = "Overall_Repeat_Rate" if "Overall_Repeat_Rate" in metric_options else metric_options[0]
    # How many dim-filter slots this row needs depends on the CURRENTLY
    # selected metric (peeked from session_state here, before the metric_col
    # widget below — persistent_selectbox reads/writes that same key, so this
    # always matches what actually renders). Reserving a fixed 4 slots
    # unconditionally — even for metrics that only use 1-2 of them — diluted
    # every column's share of the row, including Mode, so "Repeat Rate %"
    # wrapped onto its own line for every metric, not just the 4-dimension
    # one. Sizing the row to the actual dim count fixes that everywhere else
    # while still fitting all 4 pickers for Cross Sales (Platform x Acq BL).
    _peek_metric = st.session_state.get("cohort_metric", default_metric)
    if _peek_metric not in metric_options:
        _peek_metric = default_metric
    _peek_active_dims, _ = dp.get_active_dimension_filters(repeat_df, _peek_metric)
    _n_dim_slots = max(1, min(4, len(_peek_active_dims)))
    if _n_dim_slots <= 2:
        # Original (pre-3/4-level) proportions, unchanged.
        _col_ratios = [1.6] + [1.1] * _n_dim_slots + [1.3, 1.5]
    else:
        # 3-4 dim metrics (currently only Platforwise_Acq_BL_Repeat_Rate) —
        # dim chips only ever show "All"/"N selected", so they stay compact;
        # Mode/Month get a bit more than the 2-dim case since there's more
        # total row content, keeping "Repeat Rate %" on one line.
        _col_ratios = [1.3] + [0.75] * _n_dim_slots + [1.5, 1.4]
    _cohort_filter_cols = st.columns(_col_ratios)
    metric_col, mode_col, month_col = _cohort_filter_cols[0], _cohort_filter_cols[-2], _cohort_filter_cols[-1]
    dim_slot_cols = _cohort_filter_cols[1:-2]

    with metric_col:
        # Shared across Revenue/Users/Purchases/AOV on purpose (same state_key
        # regardless of active_tab) so picking a metric on one keeps it in sync
        # across the others — same intent the old auto-keyed selectbox had, but
        # immune to resetting back to the default when navigating to a non-cohort
        # tab and back (that tab's branch never reaches this line, which is
        # exactly the condition that previously caused the reset).
        metric = persistent_selectbox(
            "View", metric_options, state_key="cohort_metric", default=default_metric,
            format_func=lambda m: dp.METRIC_LABELS.get(m, m),
            label_visibility="collapsed",
            help="Choose which repeat-rate breakdown to analyze.",
        )
    active_dims, metric_sub = dp.get_active_dimension_filters(repeat_df, metric)

    # cohort_primary_dim (the FIRST active dimension, in DIMENSION_COLS order —
    # acq_business_line, cm_business_line, acq_platform, fo_val_buc) is only used
    # downstream to build the outline table's per-category sub-rows (Google-Sheets
    # style +/- expand on the table itself, see render_outline_table) — the main
    # table below is still the original combined/aggregate row per period, summing
    # every checked category together exactly as it always has.
    dim_slots = dim_slot_cols
    selections = {}
    active_dim_cols = list(active_dims.keys())
    cohort_primary_dim = active_dim_cols[0] if active_dim_cols else None
    # cohort_secondary_dim/cohort_tertiary_dim/cohort_quaternary_dim (the
    # 2nd/3rd/4th active dimensions, if any) drive the 2nd/3rd/4th levels of the
    # outline table's expand/collapse — only metrics with that many active
    # dimensions have one (currently Cross_Sell: acq_business_line x
    # cm_business_line — 2 levels; Platforwise_Acq_BL_Repeat_Rate:
    # acq_business_line x acq_platform x cm_business_line x platform — 4 levels,
    # since its cm_business_line and platform columns were populated with real
    # per-type values); every other metric has 0-1 active dims and stays
    # single-level. Generalizes automatically to any future metric with up to 4
    # active dimensions.
    cohort_secondary_dim = active_dim_cols[1] if len(active_dim_cols) > 1 else None
    cohort_tertiary_dim = active_dim_cols[2] if len(active_dim_cols) > 2 else None
    cohort_quaternary_dim = active_dim_cols[3] if len(active_dim_cols) > 3 else None
    cohort_primary_values = []
    cohort_secondary_values = []
    cohort_tertiary_values = []
    cohort_quaternary_values = []
    for i, (col, options) in enumerate(active_dims.items()):
        if i >= len(dim_slots):
            break
        ordered_options = dp.order_with_priority(options, dp.DIMENSION_PRIORITY.get(col, []))
        with dim_slots[i]:
            # No active_tab in the key: Revenue/Users/Purchases/AOV already share the
            # metric dropdown's own selection (Streamlit auto-keys it identically
            # across those tabs since its label/options are identical) — keying this
            # the same way keeps the dimension filters in sync with that, too.
            # Defaults to every option checked ("Select All") so the +/- outline
            # expand/collapse feature is visible immediately without the user
            # first having to manually check everything.
            picked = checkbox_multiselect(
                dp.DIMENSION_LABELS[col], ordered_options, key=f"{metric}_{col}", default=ordered_options,
            )
        picked = picked or ordered_options  # nothing picked = don't filter this dimension away
        selections[col] = picked
        if col == cohort_primary_dim:
            cohort_primary_values = picked
        elif col == cohort_secondary_dim:
            cohort_secondary_values = picked
        elif col == cohort_tertiary_dim:
            cohort_tertiary_values = picked
        elif col == cohort_quaternary_dim:
            cohort_quaternary_values = picked

    # The combined/aggregate table (exactly as before any outline-table changes):
    # every checked category across both dimensions summed into one row per period.
    filtered = dp.filter_df(metric_sub, selections)
    filtered = dp.with_acq_line_enrolled(
        repeat_df, filtered, metric, selections.get("acq_business_line"), acq_platform=selections.get("acq_platform")
    )
    # Secondary-only filter (excludes the primary dim) — used to build each
    # primary-category's own sub-row inside the outline table.
    secondary_selections = {c: v for c, v in selections.items() if c != cohort_primary_dim}

    show_toggle = active_tab not in ("AOV", "ARPU")
    if show_toggle:
        with mode_col:
            with st.container(key="mode_toggle"):
                view_mode = persistent_segmented_control(
                    "Mode", ["Absolute", "Repeat Rate %"], state_key="cohort_view_mode", default="Repeat Rate %",
                    label_visibility="collapsed",
                    help="Repeat Rate % divides each M0-M12+ cohort value by that month's New Acquisitions value.",
                )
    from_ts, to_ts = render_month_range(month_col)

elif active_tab == "LTV":
    _month_row, _ltv_spacer = st.columns([1.5, 8.5])
    from_ts, to_ts = render_month_range(_month_row)

elif active_tab == "Recency":
    type_col, value_col_r, mode_col_r, month_col = st.columns([1.3, 1.3, 1.3, 1.5])
    recency_sub = repeat_df[repeat_df["metric"] == "Recency"]
    cm_options = dp.unique_options(recency_sub["cm_business_line"])
    ordered_cm = dp.order_with_priority(cm_options, dp.DIMENSION_PRIORITY.get("cm_business_line", []))
    with type_col:
        # Select All by default (see the equivalent cohort-tab comment above).
        picked_cm = checkbox_multiselect("Type", ordered_cm, key="recency_type", default=ordered_cm)
    picked_cm = picked_cm or ordered_cm
    with value_col_r:
        recency_value_type = persistent_segmented_control(
            "Value", ["Revenue", "Users", "Purchases"], state_key="recency_value_type", default="Revenue",
            label_visibility="collapsed",
        )
    with mode_col_r:
        with st.container(key="recency_mode_toggle"):
            recency_mode = persistent_segmented_control(
                "Recency mode", ["Absolute", "% of Total"], state_key="recency_mode", default="% of Total",
                label_visibility="collapsed",
                help="Show each recency bucket's share of that month's total, or the raw absolute value.",
            )
    recency_filtered = recency_sub[recency_sub["cm_business_line"].isin(picked_cm)]
    from_ts, to_ts = render_month_range(month_col)

elif active_tab in PERIOD_METRIC_TABS:
    # Everything for these two tabs lives on one compact row: View dropdown, up to 3
    # context-dependent controls, Value, and the From/To month range — all always
    # visible together since these tabs' controls never go away. A single dropdown
    # for View (instead of 6 pills) is what makes fitting all of this on one line
    # possible in the first place.
    with st.container(key="pm_row"):
        view_col_pm, ctrl1_col, ctrl2_col, ctrl3_col, value_col_pm, month_col_pm = st.columns(
            [1.5, 1.1, 1.0, 0.95, 1.9, 1.3]
        )
        with view_col_pm:
            period_metric_view = persistent_selectbox(
                "View", PERIOD_METRIC_VIEWS, state_key=f"{active_tab}_view", default="Overall",
                label_visibility="collapsed",
                help="Choose which Session/Purchase Month breakdown to analyze.",
            )

        metric_name = PERIOD_METRIC_TABS[active_tab][period_metric_view]
        metric_sub_pm = repeat_df[repeat_df["metric"] == metric_name]

        if period_metric_view not in CONTRIBUTION_VIEWS:
            needs_business_line = period_metric_view in ("Business Line", "Business Line & Platform")
            needs_platform = period_metric_view in ("Platform", "Business Line & Platform")
            # pm_base_metric_sub is the metric's data BEFORE either dimension is
            # filtered — kept around so the outline table's sub-rows can re-scope
            # to a single checked category (or, for "Business Line & Platform", a
            # single business-line/platform combination) independent of whatever
            # else is checked. period_metric_filtered below is still the ORIGINAL
            # combined/aggregate row-per-period table (every checked category
            # summed together via isin, exactly as before any outline changes).
            pm_base_metric_sub = metric_sub_pm
            if needs_business_line:
                cm_options_pm = dp.unique_options(metric_sub_pm["cm_business_line"])
                ordered_cm_pm = dp.order_with_priority(cm_options_pm, dp.DIMENSION_PRIORITY.get("cm_business_line", []))
                with ctrl1_col:
                    # Select All by default (see the equivalent cohort-tab comment above).
                    picked_cm_pm = checkbox_multiselect(
                        "Type", ordered_cm_pm, key=f"{active_tab}_type", default=ordered_cm_pm,
                    )
                picked_cm_pm = picked_cm_pm or ordered_cm_pm
                pm_primary_dim, pm_primary_values = "cm_business_line", picked_cm_pm
                metric_sub_pm = metric_sub_pm[metric_sub_pm["cm_business_line"].isin(picked_cm_pm)]
            if needs_platform:
                platform_options_pm = dp.unique_options(metric_sub_pm["platform"])
                with (ctrl2_col if needs_business_line else ctrl1_col):
                    # Select All by default (see the equivalent cohort-tab comment above).
                    picked_platform_pm = checkbox_multiselect(
                        "Platform", platform_options_pm, key=f"{active_tab}_platform", default=platform_options_pm,
                    )
                picked_platform_pm = picked_platform_pm or platform_options_pm
                metric_sub_pm = metric_sub_pm[metric_sub_pm["platform"].isin(picked_platform_pm)]
                if needs_business_line:
                    # "Business Line & Platform" has two checked dimensions — the
                    # outline table flattens their cross-product into one sub-row
                    # per "Business Line / Platform" combination rather than
                    # double-nesting (see render_period_metric_tab).
                    pm_secondary_dim, pm_secondary_values = "platform", picked_platform_pm
                else:
                    pm_primary_dim, pm_primary_values = "platform", picked_platform_pm
            with value_col_pm:
                period_metric_value_type = persistent_segmented_control(
                    "Value", ["Revenue", "Users", "Purchases"], state_key=f"{active_tab}_value_type", default="Revenue",
                    label_visibility="collapsed",
                )
            period_metric_filtered = metric_sub_pm

        else:
            # "BL Contribution to Platform": break down by business line, scoped to
            # whichever platform(s) are checked. "Platform Contribution to BL": break
            # down by platform, scoped to whichever business line(s) are checked.
            # Every option checked (the default) = no filtering = contribution to the
            # OVERALL total, rather than to one specific platform/business line.
            if period_metric_view == "BL Contribution to Platform":
                contrib_breakdown_col = "cm_business_line"
                fixed_col, fixed_widget_label = "platform", "Platform"
                fixed_options = dp.unique_options(metric_sub_pm[fixed_col])
            else:
                contrib_breakdown_col = "platform"
                fixed_col, fixed_widget_label = "cm_business_line", "Business Line"
                fixed_options = dp.order_with_priority(
                    dp.unique_options(metric_sub_pm[fixed_col]), dp.DIMENSION_PRIORITY.get("cm_business_line", [])
                )
            with ctrl1_col:
                contrib_fixed_values = checkbox_multiselect(
                    fixed_widget_label, fixed_options,
                    key=f"{active_tab}_contrib_fixed_{contrib_breakdown_col}", default=fixed_options,
                )
            contrib_fixed_values = contrib_fixed_values or fixed_options
            with ctrl2_col:
                period_metric_component = persistent_segmented_control(
                    "Component", ["Overall", "New", "Repeat"], state_key=f"{active_tab}_component", default="Overall",
                    label_visibility="collapsed",
                )
            with value_col_pm:
                period_metric_value_type = persistent_segmented_control(
                    "Value", ["Revenue", "Users", "Purchases", "AOV", "ARPU"], state_key=f"{active_tab}_value_type", default="Revenue",
                    label_visibility="collapsed",
                )
            is_ratio_value = period_metric_value_type in ("AOV", "ARPU")
            with ctrl3_col:
                if is_ratio_value:
                    period_metric_contrib_mode = "Absolute"
                    st.caption("Absolute only — AOV/ARPU are averages, not additive.")
                else:
                    period_metric_contrib_mode = persistent_segmented_control(
                        "Contribution mode", ["Absolute", "% Contrib"], state_key=f"{active_tab}_contrib_mode", default="% Contrib",
                        label_visibility="collapsed",
                        help=f"Show each {'business line' if contrib_breakdown_col == 'cm_business_line' else 'platform'}'s share of the total, or the raw absolute value.",
                    )
            period_metric_filtered = (
                metric_sub_pm if set(contrib_fixed_values) == set(fixed_options)
                else metric_sub_pm[metric_sub_pm[fixed_col].isin(contrib_fixed_values)]
            )

        from_ts, to_ts = render_month_range(month_col_pm)

is_pct = (view_mode == "Repeat Rate %") and (active_tab not in ("AOV", "ARPU"))
recency_is_pct = recency_mode == "% of Total"

# Every branch above (LTV / cohort tabs / Recency / Session-Purchase Month) sets
# from_ts/to_ts inline in its own filter row now — nothing left to fall back to.
if not filtered.empty:
    filtered = filtered[(filtered["period"] >= from_ts) & (filtered["period"] <= to_ts)]
if not recency_filtered.empty:
    recency_filtered = recency_filtered[(recency_filtered["period"] >= from_ts) & (recency_filtered["period"] <= to_ts)]
if not period_metric_filtered.empty:
    period_metric_filtered = period_metric_filtered[
        (period_metric_filtered["period"] >= from_ts) & (period_metric_filtered["period"] <= to_ts)
    ]
ltv_df = ltv_df[(ltv_df["Month"] >= from_ts) & (ltv_df["Month"] <= to_ts)]

st.divider()


def render_cohort_tab(value_col, title, is_pct, currency=False, ratio_denom=None):
    """Renders the Revenue/Users/Purchases (value_col given) or AOV/ARPU
    (ratio_denom="purchases"/"users", value_col ignored — the ratio is computed
    from rev/ratio_denom per cohort column) tables for whichever metric is
    selected in the View dropdown.

    The table itself is always the original combined/aggregate row per period
    (every checked category summed together, exactly as before any outline-table
    changes). When the selected metric has a "primary" breakdown dimension with
    more than one category checked (cohort_primary_dim/cohort_primary_values, set
    in the Filters row above), each period row additionally gets a +/- control to
    expand it in place into one sub-row per checked category (Google-Sheets-style
    row outline) — see render_outline_table."""
    if filtered.empty:
        st.info("No data available for this filter combination.")
        return

    if ratio_denom:
        rev_pv = dp.pivot_cohort(filtered, "rev")
        denom_pv = dp.pivot_cohort(filtered, ratio_denom)
        pv = dp.compute_aov(rev_pv, denom_pv)
    else:
        pv = dp.pivot_cohort(filtered, value_col)
    if pv.empty or "enrolled_users" not in pv.columns:
        st.info("No data available for this filter combination.")
        return
    pv_show = dp.to_repeat_rate_pct(pv) if is_pct else pv

    mode_label = "Repeat Rate %" if is_pct else "Absolute Values"
    heading = f"{title} — {mode_label}"
    st.subheader(heading)

    pct_cols = {c for c in pv_show.columns if is_pct and c != "enrolled_users"}
    if not currency:
        currency_cols = set()
    elif is_pct:
        currency_cols = {"enrolled_users"}
    else:
        currency_cols = set(pv_show.columns)

    columns = [c for c in dp.COHORT_ORDER if c in pv_show.columns]
    gradient_cols = [c for c in columns if c != "enrolled_users"]
    cmap = dp.GREEN_HEATMAP_CMAP if is_pct else dp.BLUE_HEATMAP_CMAP

    def _acq_platform_for(l1_cat=None, l2_cat=None, l3_cat=None, l4_cat=None):
        # Mirrors the acq_for_enrolled resolution below, but for
        # acq_platform (only meaningful for PLATFORM_SELF_MATCH_METRICS,
        # currently just Cross Sales (Platform x Acq BL)): whichever level
        # currently has acq_platform fixed to one specific value contributes
        # that value; if acq_platform isn't one of the dims fixed at this
        # level (or this metric has no platform self-match at all), fall back
        # to the checked-list filter, which is a no-op for every other metric.
        if cohort_primary_dim == "acq_platform":
            return l1_cat
        if cohort_secondary_dim == "acq_platform":
            return l2_cat
        if cohort_tertiary_dim == "acq_platform":
            return l3_cat
        if cohort_quaternary_dim == "acq_platform":
            return l4_cat
        return selections.get("acq_platform")

    def sub_df_fn(cat):
        if cohort_primary_dim is None:
            return None
        cat_df = dp.filter_df(metric_sub, {**secondary_selections, cohort_primary_dim: cat})
        acq_for_enrolled = cat if cohort_primary_dim == "acq_business_line" else selections.get("acq_business_line")
        cat_df = dp.with_acq_line_enrolled(
            repeat_df, cat_df, metric, acq_for_enrolled, acq_platform=_acq_platform_for(l1_cat=cat)
        )
        cat_df = cat_df[(cat_df["period"] >= from_ts) & (cat_df["period"] <= to_ts)]
        if ratio_denom:
            r = dp.pivot_cohort(cat_df, "rev")
            d_ = dp.pivot_cohort(cat_df, ratio_denom)
            sub_pv = dp.compute_aov(r, d_)
        else:
            sub_pv = dp.pivot_cohort(cat_df, value_col)
        return dp.to_repeat_rate_pct(sub_pv) if is_pct else sub_pv

    def secondary_sub_df_fn(l1_cat, l2_cat):
        # Fixes BOTH dimensions at once — l1_cat for cohort_primary_dim (e.g. an
        # Acquisition Business Line) and l2_cat for cohort_secondary_dim (e.g. a
        # CM Business Line, or an Acquisition Platform) — for the second level
        # of the outline table's expand/collapse (only reached when the
        # selected metric has 2 active dimensions, e.g. Cross Sales / Cross
        # Sales (Platform x Acq BL)).
        if cohort_primary_dim is None or cohort_secondary_dim is None:
            return None
        filt = {c: v for c, v in selections.items() if c not in (cohort_primary_dim, cohort_secondary_dim)}
        filt[cohort_primary_dim] = l1_cat
        filt[cohort_secondary_dim] = l2_cat
        cat_df = dp.filter_df(metric_sub, filt)
        if cohort_primary_dim == "acq_business_line":
            acq_for_enrolled = l1_cat
        elif cohort_secondary_dim == "acq_business_line":
            acq_for_enrolled = l2_cat
        else:
            acq_for_enrolled = selections.get("acq_business_line")
        cat_df = dp.with_acq_line_enrolled(
            repeat_df, cat_df, metric, acq_for_enrolled, acq_platform=_acq_platform_for(l1_cat=l1_cat, l2_cat=l2_cat)
        )
        cat_df = cat_df[(cat_df["period"] >= from_ts) & (cat_df["period"] <= to_ts)]
        if ratio_denom:
            r = dp.pivot_cohort(cat_df, "rev")
            d_ = dp.pivot_cohort(cat_df, ratio_denom)
            sub_pv = dp.compute_aov(r, d_)
        else:
            sub_pv = dp.pivot_cohort(cat_df, value_col)
        return dp.to_repeat_rate_pct(sub_pv) if is_pct else sub_pv

    def tertiary_sub_df_fn(l1_cat, l2_cat, l3_cat):
        # Fixes all three dimensions — for the THIRD level of the outline
        # table's expand/collapse (only reached when the selected metric has 3
        # active dimensions, currently just Cross Sales (Platform x Acq BL)
        # now that its cm_business_line column has real per-type values).
        if cohort_primary_dim is None or cohort_secondary_dim is None or cohort_tertiary_dim is None:
            return None
        excluded = (cohort_primary_dim, cohort_secondary_dim, cohort_tertiary_dim)
        filt = {c: v for c, v in selections.items() if c not in excluded}
        filt[cohort_primary_dim] = l1_cat
        filt[cohort_secondary_dim] = l2_cat
        filt[cohort_tertiary_dim] = l3_cat
        cat_df = dp.filter_df(metric_sub, filt)
        if cohort_primary_dim == "acq_business_line":
            acq_for_enrolled = l1_cat
        elif cohort_secondary_dim == "acq_business_line":
            acq_for_enrolled = l2_cat
        elif cohort_tertiary_dim == "acq_business_line":
            acq_for_enrolled = l3_cat
        else:
            acq_for_enrolled = selections.get("acq_business_line")
        cat_df = dp.with_acq_line_enrolled(
            repeat_df, cat_df, metric, acq_for_enrolled,
            acq_platform=_acq_platform_for(l1_cat=l1_cat, l2_cat=l2_cat, l3_cat=l3_cat),
        )
        cat_df = cat_df[(cat_df["period"] >= from_ts) & (cat_df["period"] <= to_ts)]
        if ratio_denom:
            r = dp.pivot_cohort(cat_df, "rev")
            d_ = dp.pivot_cohort(cat_df, ratio_denom)
            sub_pv = dp.compute_aov(r, d_)
        else:
            sub_pv = dp.pivot_cohort(cat_df, value_col)
        return dp.to_repeat_rate_pct(sub_pv) if is_pct else sub_pv

    def quaternary_sub_df_fn(l1_cat, l2_cat, l3_cat, l4_cat):
        # Fixes all four dimensions — for the FOURTH level of the outline
        # table's expand/collapse (only reached when the selected metric has 4
        # active dimensions, currently just Cross Sales (Platform x Acq BL)
        # now that its cm_business_line AND platform columns both have real
        # per-type values).
        if None in (cohort_primary_dim, cohort_secondary_dim, cohort_tertiary_dim, cohort_quaternary_dim):
            return None
        excluded = (cohort_primary_dim, cohort_secondary_dim, cohort_tertiary_dim, cohort_quaternary_dim)
        filt = {c: v for c, v in selections.items() if c not in excluded}
        filt[cohort_primary_dim] = l1_cat
        filt[cohort_secondary_dim] = l2_cat
        filt[cohort_tertiary_dim] = l3_cat
        filt[cohort_quaternary_dim] = l4_cat
        cat_df = dp.filter_df(metric_sub, filt)
        if cohort_primary_dim == "acq_business_line":
            acq_for_enrolled = l1_cat
        elif cohort_secondary_dim == "acq_business_line":
            acq_for_enrolled = l2_cat
        elif cohort_tertiary_dim == "acq_business_line":
            acq_for_enrolled = l3_cat
        elif cohort_quaternary_dim == "acq_business_line":
            acq_for_enrolled = l4_cat
        else:
            acq_for_enrolled = selections.get("acq_business_line")
        cat_df = dp.with_acq_line_enrolled(
            repeat_df, cat_df, metric, acq_for_enrolled,
            acq_platform=_acq_platform_for(l1_cat=l1_cat, l2_cat=l2_cat, l3_cat=l3_cat, l4_cat=l4_cat),
        )
        cat_df = cat_df[(cat_df["period"] >= from_ts) & (cat_df["period"] <= to_ts)]
        if ratio_denom:
            r = dp.pivot_cohort(cat_df, "rev")
            d_ = dp.pivot_cohort(cat_df, ratio_denom)
            sub_pv = dp.compute_aov(r, d_)
        else:
            sub_pv = dp.pivot_cohort(cat_df, value_col)
        return dp.to_repeat_rate_pct(sub_pv) if is_pct else sub_pv

    periods = list(pv_show.index)
    table_key = f"cohort_{title}_{metric}_{mode_label}".replace(" ", "_")
    l2_kwargs = dict(
        primary_dim_label=dp.DIMENSION_LABELS.get(cohort_primary_dim, cohort_primary_dim),
        secondary_dim_label=dp.DIMENSION_LABELS.get(cohort_secondary_dim, cohort_secondary_dim),
        secondary_categories=cohort_secondary_values if cohort_secondary_dim else None,
        secondary_sub_df_fn=secondary_sub_df_fn if cohort_secondary_dim else None,
        tertiary_dim_label=dp.DIMENSION_LABELS.get(cohort_tertiary_dim, cohort_tertiary_dim),
        tertiary_categories=cohort_tertiary_values if cohort_tertiary_dim else None,
        tertiary_sub_df_fn=tertiary_sub_df_fn if cohort_tertiary_dim else None,
        quaternary_dim_label=dp.DIMENSION_LABELS.get(cohort_quaternary_dim, cohort_quaternary_dim),
        quaternary_categories=cohort_quaternary_values if cohort_quaternary_dim else None,
        quaternary_sub_df_fn=quaternary_sub_df_fn if cohort_quaternary_dim else None,
        # acq_business_line/cm_business_line and acq_platform/platform each
        # share the exact same category vocabulary within their pair (e.g.
        # "Group Online" is a value of both business-line columns; "ANDROID"
        # is a value of both platform columns) — a short " Acq" suffix on
        # Acquisition Business Line rows and a "CM " prefix on CM Business
        # Line/CM Platform rows disambiguates every single row, not just via
        # the one-time "Rows expand: ..." caption. Scoped to the actual column
        # identity (not just "whichever is primary/secondary/tertiary/
        # quaternary") so this only fires for these specific dimensions,
        # wherever they end up in the hierarchy (CM Business Line is level 2
        # for Cross Sales, but level 3 for Cross Sales (Platform x Acq BL) —
        # see DIMENSION_COLS' ordering comment in data_processing.py).
        primary_row_suffix=" Acq" if cohort_primary_dim == "acq_business_line" else "",
        secondary_row_prefix="CM " if cohort_secondary_dim == "cm_business_line" else "",
        tertiary_row_prefix="CM " if cohort_tertiary_dim == "cm_business_line" else "",
        quaternary_row_prefix="CM " if cohort_quaternary_dim == "platform" else "",
    ) if cohort_secondary_dim else {}
    disp_df = render_outline_table(
        table_key, periods, pv_show, cohort_primary_values, sub_df_fn, columns, dp.COHORT_LABELS,
        pct_cols, currency_cols, cmap=cmap, gradient_cols=gradient_cols, **l2_kwargs,
    )
    download_csv_button(disp_df, f"{table_key}.csv", key=f"dl_{table_key}")

    render_outline_diff_table(
        table_key, periods, pv_show, cohort_primary_values, sub_df_fn, columns, dp.COHORT_LABELS,
        pct_cols=pct_cols, currency_cols=currency_cols, title=heading,
        chart_mode="trend", chart_col="enrolled_users", chart_y_title="New Acquisitions", **l2_kwargs,
    )

    st.plotly_chart(
        ch.single_bar(
            pv.index.strftime("%b-%Y"), pv["enrolled_users"],
            f"New Acquisitions by Month — {title}", y_title="New Acquisitions",
        ),
        use_container_width=True,
    )
    cohort_cols = [c for c in dp.COHORT_ORDER if c != "enrolled_users" and c in pv_show.columns]
    st.plotly_chart(
        ch.stacked_cohort_bar(
            pv_show, cohort_cols, dp.COHORT_LABELS,
            f"Repeat Distribution by Acquisition Month — {title}", is_pct=is_pct,
        ),
        use_container_width=True,
    )


def render_recency_tab(value_type, is_pct):
    if recency_filtered.empty:
        st.info("No data available for this filter combination.")
        return

    value_col = {"Revenue": "rev", "Users": "users", "Purchases": "purchases"}[value_type]
    pv = dp.pivot_recency(recency_filtered, value_col)
    bucket_cols = [c for c in dp.RECENCY_ORDER if c in pv.columns]
    pv_total = dp.with_total_column(pv, bucket_cols)
    pv_show = dp.to_contribution_pct(pv_total, bucket_cols) if is_pct else pv_total
    disp = dp.relabel(pv_show, dp.RECENCY_LABELS)

    mode_label = "% of Total" if is_pct else "Absolute Values"
    st.subheader(f"{value_type} Recency — {mode_label}")
    st.caption(
        "How current-month activity breaks down by recency of the user's last engagement — "
        "a composition of Total, not a repeat-rate cohort."
    )

    if value_type != "Revenue":
        currency_cols = set()
    elif is_pct:
        currency_cols = {"Total"}
    else:
        currency_cols = set(disp.columns)
    pct_cols = {c for c in disp.columns if is_pct and c != "Total"}
    formatted = dp.format_table(disp, pct_cols, currency_cols)
    # Raw (pre-relabel) equivalents — pv_show/pv_total still use the sheet's own
    # recency bucket codes ('8-14days', ...), not RECENCY_LABELS' display text.
    raw_pct_cols = {c for c in pv_show.columns if is_pct and c != "Total"}
    raw_currency_cols = set(pv_show.columns) if (value_type == "Revenue" and not is_pct) else (
        {"Total"} if (value_type == "Revenue" and is_pct) else set()
    )
    gradient_cols = [c for c in disp.columns if c != "Total"]
    cmap = dp.TEAL_HEATMAP_CMAP if is_pct else dp.VIOLET_HEATMAP_CMAP
    st.table(dp.styled_cohort_table(formatted, disp, gradient_cols, cmap=cmap))
    download_csv_button(disp, f"Recency_{value_type}_{mode_label}.csv".replace(" ", "_"), key=f"dl_recency_{value_type}_{mode_label}")

    # Diff table goes directly below the main table, before any chart. Recency
    # has no checked-category breakdown to expand/collapse (its buckets are
    # always all shown as columns), so this renders with no +/- control at all.
    render_outline_diff_table(
        f"recency_{value_type}_{mode_label}".replace(" ", "_"), list(pv_show.index), pv_show, [], lambda cat: None,
        ["Total"] + bucket_cols, dp.RECENCY_LABELS, pct_cols=raw_pct_cols, currency_cols=raw_currency_cols,
        emphasize_cols=["Total"], title=f"{value_type} Recency ({mode_label})",
        chart_mode="latest_by_category", chart_y_title=f"{value_type} Change",
    )

    st.plotly_chart(
        ch.single_bar(
            pv_total.index.strftime("%b-%Y"), pv_total["Total"],
            f"Total {value_type} by Month", y_title=f"Total {value_type}",
            color=ch.CATEGORICAL[4],
        ),
        use_container_width=True,
    )
    st.plotly_chart(
        ch.stacked_cohort_bar(
            pv_show, bucket_cols, dp.RECENCY_LABELS,
            f"Recency Distribution by Month — {value_type}", is_pct=is_pct,
            pct_axis_title="% of Total",
        ),
        use_container_width=True,
    )


def render_period_metric_tab(tab_title, value_type, view_label):
    """The table is always the original combined/aggregate row per period (every
    checked category summed together via isin, exactly as before any outline
    changes). When pm_primary_dim is set with more than one category checked
    (Business Line groups by cm_business_line, Platform groups by platform,
    Business Line & Platform flattens the cross-product of both into combined
    "Business Line / Platform" categories — see the Filters row above), each
    period row gets a +/- to expand it into one sub-row per category."""
    if period_metric_filtered.empty:
        st.info("No data available for this filter combination.")
        return

    # Platform Fees isn't a real business line — it's an extra charge on a purchase
    # that already belongs to some other business line. Summing Users across every
    # checked business line (Business Line / Business Line & Platform views only)
    # would double-count those users if Platform Fees' own rows were included, so
    # exclude them from that combined total. Revenue/Purchases/AOV are untouched,
    # and views with no business-line dimension active (Overall, Platform) never
    # hit this at all.
    _business_line_in_view = pm_primary_dim == "cm_business_line" or pm_secondary_dim == "cm_business_line"

    def _compute_combined(df_scope, base_value_type=value_type):
        p_scope = dp.exclude_platform_fees(df_scope) if (base_value_type == "Users" and _business_line_in_view) else df_scope
        p_ = dp.pivot_period_metric(p_scope, base_value_type)
        p_pct = dp.with_new_repeat_pct(p_)
        r_ = p_ if base_value_type == "Revenue" else dp.pivot_period_metric(df_scope, "Revenue")
        pu_ = p_ if base_value_type == "Purchases" else dp.pivot_period_metric(df_scope, "Purchases")
        a_ = dp.compute_aov(r_, pu_)
        a_named = a_.rename(columns={"Total": "AOV Total", "New": "AOV New", "Repeat": "AOV Repeat"})
        # ARPU = Total Revenue / Total Users — Total only, not split by New/Repeat
        # (per request). Its Users denominator gets the same Platform-Fees
        # exclusion as the Users pivot above, so it stays consistent with
        # whatever Total Users this same table is already showing.
        u_scope = dp.exclude_platform_fees(df_scope) if _business_line_in_view else df_scope
        u_ = p_ if base_value_type == "Users" else dp.pivot_period_metric(u_scope, "Users")
        arpu_ = dp.safe_divide_series(r_["Total"], u_["Total"]).rename("ARPU").to_frame()
        return p_, p_pct, a_, p_pct.join(a_named, how="left").join(arpu_, how="left")

    pv, pv_pct, aov_pv, combined = _compute_combined(period_metric_filtered)

    heading = f"{tab_title} ({view_label}) — {value_type}"
    st.subheader(heading)
    st.caption("Total / New / Repeat as tracked directly in the source data — not a repeat-rate cohort.")

    base_cols = ["Total", "New", "Repeat"]
    pct_cols = {"New %", "Repeat %"}
    aov_cols = ["AOV Total", "AOV New", "AOV Repeat"]
    arpu_cols = ["ARPU"]
    currency_cols = (set(base_cols) if value_type == "Revenue" else set()) | set(aov_cols) | set(arpu_cols)
    columns = list(combined.columns)
    groups = [
        (base_cols, dp.BLUE_HEATMAP_CMAP), (list(pct_cols), dp.GREEN_HEATMAP_CMAP),
        (aov_cols, dp.VIOLET_HEATMAP_CMAP), (arpu_cols, dp.TEAL_HEATMAP_CMAP),
    ]

    def sub_df_fn(cat):
        if pm_secondary_dim:
            bl, pf = cat.split(" / ", 1)
            scope = pm_base_metric_sub[
                (pm_base_metric_sub[pm_primary_dim] == bl) & (pm_base_metric_sub[pm_secondary_dim] == pf)
            ]
        elif pm_primary_dim:
            scope = pm_base_metric_sub[pm_base_metric_sub[pm_primary_dim] == cat]
        else:
            return None
        scope = scope[(scope["period"] >= from_ts) & (scope["period"] <= to_ts)]
        if scope.empty:
            return None
        return _compute_combined(scope)[3]

    if pm_secondary_dim:
        # "Business Line & Platform" — flatten the cross-product rather than
        # double-nesting, per the sub-row design; nothing to expand if both
        # dimensions only have a single value checked.
        if len(pm_primary_values) <= 1 and len(pm_secondary_values) <= 1:
            category_list = []
        else:
            category_list = [f"{bl} / {pf}" for bl in pm_primary_values for pf in pm_secondary_values]
    else:
        category_list = pm_primary_values if pm_primary_dim else []

    periods = list(combined.index)
    table_key = f"pm_{tab_title}_{view_label}_{value_type}".replace(" ", "_")
    disp_df = render_outline_table(
        table_key, periods, combined, category_list, sub_df_fn, columns, {},
        pct_cols, currency_cols, groups=groups,
    )
    download_csv_button(disp_df, f"{table_key}.csv", key=f"dl_{table_key}")

    render_outline_diff_table(
        table_key, periods, combined, category_list, sub_df_fn, columns, {},
        pct_cols=pct_cols, currency_cols=currency_cols, emphasize_cols=["Total", "AOV Total"],
        title=heading, chart_mode="trend", chart_col="Total", chart_y_title=value_type,
    )

    st.plotly_chart(
        ch.new_repeat_bar(
            pv.index.strftime("%b-%Y"), pv["New"], pv["Repeat"],
            f"New vs Repeat {value_type} by Month — {tab_title} ({view_label})", y_title=value_type,
        ),
        use_container_width=True,
    )

    pct_chart_df = pv_pct.reset_index()
    pct_chart_df["Month"] = pct_chart_df["period"].dt.strftime("%b-%Y")
    st.plotly_chart(
        ch.multi_line(
            pct_chart_df, "Month", ["New %", "Repeat %"], {"New %": "New %", "Repeat %": "Repeat %"},
            f"New % vs Repeat % Trend — {tab_title} ({view_label}, {value_type})", y_title="% of Total",
        ),
        use_container_width=True,
    )

    aov_disp = aov_pv.reset_index()
    aov_disp["Month"] = aov_disp["period"].dt.strftime("%b-%Y")
    st.plotly_chart(
        ch.multi_line(
            aov_disp, "Month", ["Total", "New", "Repeat"],
            {"Total": "Total AOV", "New": "New AOV", "Repeat": "Repeat AOV"},
            f"AOV Trend — {tab_title} ({view_label})", y_title="AOV (₹)",
        ),
        use_container_width=True,
    )


def render_contribution_tab(tab_title, value_type, component, breakdown_col, fixed_values, fixed_options, is_pct):
    """'BL Contribution to Platform' / 'Platform Contribution to BL' — how much of
    the selected platform(s)'/business line(s)' Total/New/Repeat Rev/Users/
    Purchases (or AOV/ARPU) each business line (or each platform) contributes,
    per month. Every option in fixed_options checked (the default) is equivalent
    to no filter at all — that's what gives contribution to the OVERALL total.

    The table is always the original combined row per period (every checked
    fixed value summed together, exactly as before any outline changes). When
    more than one fixed value is checked, each period row additionally gets a
    +/- to expand it into one sub-row per checked fixed value (e.g. its own
    contribution-to-ANDROID row, contribution-to-IOS row, ...), so the user can
    see every checked value's own breakdown without unchecking the others."""
    if period_metric_filtered.empty or not fixed_values:
        st.info("No data available for this filter combination.")
        return

    breakdown_label = "Business Line" if breakdown_col == "cm_business_line" else "Platform"
    fixed_label = "Platform" if breakdown_col == "cm_business_line" else "Business Line"
    fixed_col = "platform" if breakdown_col == "cm_business_line" else "cm_business_line"
    is_ratio = value_type in ("AOV", "ARPU")
    local_is_pct = False if is_ratio else is_pct
    component_idx = {"Overall": 0, "New": 1, "Repeat": 2}[component]

    def _compute_pivot(df_scope):
        if is_ratio:
            num_col = dp.PERIOD_METRIC_SOURCE_COLS["Revenue"][component_idx]
            den_col = dp.PERIOD_METRIC_SOURCE_COLS["Purchases" if value_type == "AOV" else "Users"][component_idx]
            num_pv = dp.pivot_by_dimension(df_scope, breakdown_col, num_col)
            den_pv = dp.pivot_by_dimension(df_scope, breakdown_col, den_col)
            bcols = sorted(set(num_pv.columns) | set(den_pv.columns))
            if breakdown_col == "cm_business_line":
                bcols = dp.order_with_priority(bcols, dp.DIMENSION_PRIORITY.get("cm_business_line", []))
            pv = dp.compute_aov(num_pv.reindex(columns=bcols), den_pv.reindex(columns=bcols))
            # ARPU's Users denominator: exclude Platform Fees from the TRUE total (it's
            # not a real business line, so its users shouldn't be double-counted into
            # the combined total) while each business line's/platform's own bucket
            # above — including Platform Fees' own column, if it is one — stays as-is.
            den_scope = dp.exclude_platform_fees(df_scope) if value_type == "ARPU" else df_scope
            true_ratio = dp.safe_divide_series(
                dp.true_period_total(df_scope, num_col), dp.true_period_total(den_scope, den_col),
            )
            pv_total = pv.copy()
            pv_total.insert(0, "Total", true_ratio.reindex(pv_total.index))
            return pv_total, pv_total, bcols
        source_cols = dp.PERIOD_METRIC_SOURCE_COLS[value_type]  # (total_col, new_col, repeat_col)
        value_col = source_cols[component_idx]
        pv = dp.pivot_by_dimension(df_scope, breakdown_col, value_col)
        bcols = list(pv.columns)
        bcols = dp.order_with_priority(bcols, dp.DIMENSION_PRIORITY.get("cm_business_line", [])) if breakdown_col == "cm_business_line" else sorted(bcols)
        pv = pv[bcols]
        # "Total" is the true, dimension-agnostic period total (see true_period_total's
        # docstring) — not just the sum of the named buckets, which would silently
        # shrink whenever some revenue's breakdown_col happens to be untagged.
        # For Users specifically, also exclude Platform Fees from that true total —
        # it isn't a real business line, so its users would double-count against
        # whichever real business line the purchase actually belongs to. Each
        # business line's/platform's own bucket column above is left untouched.
        total_scope = dp.exclude_platform_fees(df_scope) if value_type == "Users" else df_scope
        true_total = dp.true_period_total(total_scope, value_col)
        pv_total = pv.copy()
        pv_total.insert(0, "Total", true_total.reindex(pv_total.index))
        pv_show = dp.to_contribution_pct(pv_total, bcols) if local_is_pct else pv_total
        return pv_total, pv_show, bcols

    agg_pv_total, agg_pv_show, agg_bucket_cols = _compute_pivot(period_metric_filtered)

    # Sub-rows: one per checked fixed value (only meaningful with 2+ checked).
    # Bucket columns can differ slightly per scope (a business line might not
    # show up for every platform) — union them so the header stays stable
    # across the aggregate row and every sub-row.
    category_list = fixed_values if len(fixed_values) > 1 else []
    all_bucket_cols = set(agg_bucket_cols)
    sub_cache = {}
    for v in category_list:
        sub_scope = period_metric_filtered[period_metric_filtered[fixed_col] == v]
        if sub_scope.empty:
            sub_cache[v] = None
            continue
        _, sub_pv_show, sub_bcols = _compute_pivot(sub_scope)
        all_bucket_cols |= set(sub_bcols)
        sub_cache[v] = sub_pv_show
    bucket_cols = (
        dp.order_with_priority(list(all_bucket_cols), dp.DIMENSION_PRIORITY.get("cm_business_line", []))
        if breakdown_col == "cm_business_line" else sorted(all_bucket_cols)
    )
    columns = ["Total"] + bucket_cols
    agg_pv_show = agg_pv_show.reindex(columns=columns)

    def sub_df_fn(v):
        cached = sub_cache.get(v)
        return cached.reindex(columns=columns) if cached is not None else None

    is_overall = set(fixed_values) == set(fixed_options)
    if is_overall:
        target_desc, target_desc_lower, chart_target = "the Overall Total", "the overall total", "Overall Total"
    elif len(fixed_values) == 1:
        # Exactly one value checked: the fixed-dimension picker already shows it
        # (e.g. "Platform: ANDROID"), so it isn't repeated here.
        target_desc = f"the Selected {fixed_label}'s Total"
        target_desc_lower = f"the selected {fixed_label.lower()}'s total"
        chart_target = fixed_values[0]
    else:
        target_desc = f"the {len(fixed_values)} Selected {fixed_label}s (Combined)"
        target_desc_lower = f"the combined total of the {len(fixed_values)} selected {fixed_label.lower()}s"
        chart_target = f"{len(fixed_values)} {fixed_label}s combined"

    mode_label = "% Contribution" if local_is_pct else "Absolute Values"
    heading = f"{tab_title} — {breakdown_label} Contribution to {target_desc} ({mode_label})"
    st.subheader(heading)
    st.caption(
        f"{component} {value_type} — share contributed by each {breakdown_label.lower()} "
        f"to {target_desc_lower}, per month. Not a repeat-rate cohort."
    )

    if is_ratio:
        currency_cols = set(columns)  # AOV/ARPU are always ₹ figures, regardless of value_type
    elif value_type != "Revenue":
        currency_cols = set()
    elif local_is_pct:
        currency_cols = {"Total"}
    else:
        currency_cols = set(columns)
    pct_cols = {c for c in columns if local_is_pct and c != "Total"}
    cmap = dp.TEAL_HEATMAP_CMAP if local_is_pct else dp.VIOLET_HEATMAP_CMAP
    gradient_cols = [c for c in columns if c != "Total"]

    periods = list(agg_pv_show.index)
    table_key = f"contrib_{tab_title}_{breakdown_col}_{value_type}".replace(" ", "_")
    disp_df = render_outline_table(
        table_key, periods, agg_pv_show, category_list, sub_df_fn, columns, {},
        pct_cols, currency_cols, cmap=cmap, gradient_cols=gradient_cols,
    )
    download_csv_button(disp_df, f"{table_key}.csv", key=f"dl_{table_key}")

    render_outline_diff_table(
        table_key, periods, agg_pv_show, category_list, sub_df_fn, columns, {},
        pct_cols=pct_cols, currency_cols=currency_cols, emphasize_cols=["Total"],
        title=heading, chart_mode="latest_by_category",
        chart_y_title=(f"{value_type} (₹)" if is_ratio else f"Total {value_type}"),
    )

    y_title = f"{value_type} (₹)" if is_ratio else f"Total {value_type}"
    st.plotly_chart(
        ch.single_bar(
            agg_pv_total.index.strftime("%b-%Y"), agg_pv_total["Total"],
            f"Total {value_type} ({component}) — {chart_target}", y_title=y_title,
            color=ch.CATEGORICAL[4],
        ),
        use_container_width=True,
    )
    nominal_colors = [ch.CATEGORICAL[i % len(ch.CATEGORICAL)] for i in range(len(bucket_cols))]
    st.plotly_chart(
        ch.stacked_cohort_bar(
            agg_pv_show, bucket_cols, {c: c for c in bucket_cols},
            f"{breakdown_label} Contribution by Month — {chart_target}", is_pct=local_is_pct,
            pct_axis_title="% Contribution", colors=nominal_colors,
        ),
        use_container_width=True,
    )


# ---------------------------------------------------------------- LTV tab ---
if active_tab == "LTV":
    st.subheader("LTV Overview")
    st.caption("Sourced from the LTV worksheet — not affected by the filters above.")

    segments = ["Overall", "Group Online", "Group Offline", "One On One"]

    disp_ltv = ltv_df.copy()
    disp_ltv["Month"] = disp_ltv["Month"].dt.strftime("%b-%Y")
    disp_ltv = disp_ltv.set_index("Month")
    currency_cols = {f"{seg} Rev" for seg in segments} | {f"{seg} LTV" for seg in segments}
    formatted_ltv = pd.DataFrame(index=disp_ltv.index)
    for c in disp_ltv.columns:
        prefix = "₹" if c in currency_cols else ""
        formatted_ltv[c] = disp_ltv[c].map(lambda v: f"{prefix}{v:,.0f}" if pd.notna(v) else "–")
    st.dataframe(formatted_ltv, use_container_width=True, height=dp.table_height(len(formatted_ltv)))
    download_csv_button(disp_ltv, "LTV_Overview.csv", key="dl_ltv")

    ltv_cols = [f"{seg} LTV" for seg in segments]
    rev_cols = [f"{seg} Rev" for seg in segments]
    acq_cols = ["Overall Acqusitions"] + [f"{seg} Acquisitions" for seg in segments[1:]]
    seg_labels = {**{f"{s} LTV": s for s in segments}, **{f"{s} Rev": s for s in segments},
                  "Overall Acqusitions": "Overall",
                  **{f"{s} Acquisitions": s for s in segments[1:]}}

    st.plotly_chart(
        ch.multi_line(ltv_df, "Month", ltv_cols, seg_labels, "LTV Trend by Business Line", y_title="LTV (₹)", emphasize_first=True),
        use_container_width=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(
            ch.multi_line(ltv_df, "Month", rev_cols, seg_labels, "Revenue Trend by Business Line", y_title="Revenue (₹)", emphasize_first=True),
            use_container_width=True,
        )
    with c2:
        st.plotly_chart(
            ch.grouped_bar(ltv_df, "Month", acq_cols, seg_labels, "New Acquisitions by Business Line", y_title="Acquisitions"),
            use_container_width=True,
        )

    st.markdown("#### Acquisitions vs LTV, by Segment")
    x_labels = ltv_df["Month"].dt.strftime("%b-%Y")
    combo_cols = st.columns(2)
    for i, seg in enumerate(segments):
        acq_col = "Overall Acqusitions" if seg == "Overall" else f"{seg} Acquisitions"
        with combo_cols[i % 2]:
            st.plotly_chart(
                ch.combo_bar_line(
                    x_labels, ltv_df[acq_col], ltv_df[f"{seg} LTV"],
                    "Acquisitions", "LTV", f"{seg}: Acquisitions vs LTV",
                    bar_y_title="Acquisitions", line_y_title="LTV (₹)",
                    bar_color=ch.CATEGORICAL[i % len(ch.CATEGORICAL)],
                ),
                use_container_width=True,
            )

# ------------------------------------------------------- Revenue/Users/Purchases ---
elif active_tab == "Revenue":
    render_cohort_tab("rev", "Revenue", is_pct, currency=True)
elif active_tab == "Users":
    render_cohort_tab("users", "Users", is_pct, currency=False)
elif active_tab == "Purchases":
    render_cohort_tab("purchases", "Purchases", is_pct, currency=False)

# ------------------------------------------------------------------ AOV tab ---
elif active_tab == "AOV":
    st.caption("AOV is always shown in absolute terms — the Repeat Rate % toggle does not apply here.")
    render_cohort_tab(None, "AOV", is_pct=False, currency=True, ratio_denom="purchases")

# ----------------------------------------------------------------- ARPU tab ---
elif active_tab == "ARPU":
    st.caption("ARPU is always shown in absolute terms — the Repeat Rate % toggle does not apply here.")
    render_cohort_tab(None, "ARPU", is_pct=False, currency=True, ratio_denom="users")

# --------------------------------------------------------------- Recency tab ---
elif active_tab == "Recency":
    render_recency_tab(recency_value_type, recency_is_pct)

# ------------------------------------------------- Session / Purchase Month tabs ---
elif active_tab in PERIOD_METRIC_TABS:
    if period_metric_view in CONTRIBUTION_VIEWS:
        render_contribution_tab(
            active_tab, period_metric_value_type, period_metric_component,
            contrib_breakdown_col, contrib_fixed_values, fixed_options,
            period_metric_contrib_mode == "% Contrib",
        )
    else:
        render_period_metric_tab(active_tab, period_metric_value_type, period_metric_view)
