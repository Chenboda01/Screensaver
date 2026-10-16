# KDE settings design contract

The settings module uses the existing Kirigami and Qt Quick Controls component system and the user's Plasma theme. It inherits palette, typography, focus indicators, control heights, and disabled styling from those components.

## Location search

Use a native TextField with the existing FormLayout label column. Suggestions use ItemDelegate rows in a bounded ListView, with native highlighted selection. The search field owns arrow-key navigation and Enter selection; Escape dismisses suggestions. Mouse and keyboard must select the same stored place. Search status and the selected place use wrapping Labels. All widths follow the form, and spacing uses Kirigami.Units.

Typing is transient. Selecting a result changes pending settings; Apply persists and Discard reloads. Disabled Live Sky disables the field and cancels network activity. No bespoke colors, motion, icons, or typography are introduced.
