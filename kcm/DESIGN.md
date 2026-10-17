# ScreenBot KDE Settings

## 1. Atmosphere & Identity
Native Plasma settings, using Kirigami forms and Qt Quick Controls. Disclosure headers provide a compact overview without adding a separate visual style.

## 2. Color
Use Kirigami.Theme textColor, disabledTextColor and native control palettes. Existing countdown gradient conveys elapsed time and remains unchanged.

## 3. Typography
Use the desktop's default font; section titles use bold body text. Summaries use normal body text and elide at the available width.

## 4. Spacing & Layout
Use Kirigami.Units.smallSpacing and largeSpacing. SimpleKCM owns vertical scrolling. Section forms share twinFormLayouts for aligned labels, and collapse to narrow form layout using Kirigami's native behavior.

## 5. Components
CollapsibleSection: full-width native ToolButton header, arrow, title, pending-change dot, one-line collapsed summary, and a clipped FormLayout body. States: expanded, collapsed, pending, hovered, pressed, keyboard focused. Tab reaches headers; Space/Enter toggles; Left/Right collapses/expands. Hidden fields leave the focus chain. Accessible expandable/expanded state and full summary are announced. PresetChooser retains its illustrated preset cards and uses the platform performance icon for the three quality tiers; each card exposes its selected state and a description with frame-rate and battery tradeoffs. CitySearch and other controls retain their existing behavior.

## Location search

Use a native TextField with the existing FormLayout label column. Suggestions use ItemDelegate rows in a bounded ListView, with native highlighted selection. The search field owns arrow-key navigation and Enter selection; Escape dismisses suggestions. Mouse and keyboard must select the same stored place. Search status and the selected place use wrapping Labels. All widths follow the form, and spacing uses Kirigami.Units.

Typing is transient. Selecting a result changes pending settings; Apply persists and Discard reloads. Disabled Live Sky disables the field and cancels network activity. No bespoke colors, motion, icons, or typography are introduced.

## 6. Motion & Interaction
Disclosure height transitions use Kirigami.Units.shortDuration, which respects KDE animation speed including disabled animations. First render does not animate. UI expansion persists immediately in a separate settings file; product values still require Apply.

## 7. Depth & Surface
Use the platform ToolButton background for hover, press, and focus feedback. No custom elevation, colors, borders, or radii.

## 8. Accessibility Constraints & Accepted Debt
Preserve native control semantics, high-contrast and dark/light palettes. Headers expose expandable state and unsaved status. All fields remain keyboard reachable when open. Screen reader behavior is inspected through Qt accessibility interfaces in the UI test.
