# CSS standard (sources: MDN, WCAG 2.2 AA)
- CSS-01 Mobile first: base styles for small screens, `min-width` media queries for larger ones.
- CSS-02 Use CSS custom properties for colours, spacing and fonts; no repeated magic values.
- CSS-03 Layout with flexbox/grid; avoid fixed heights and absolute positioning for page layout.
- CSS-04 Relative units (`rem`, `%`, `clamp()`) for type and spacing; never set `font-size` below 16px for body text.
- CSS-05 Keep specificity low: classes, not ids or long selector chains; no `!important` except to override third-party CSS.
- CSS-06 Visible `:focus-visible` styles; never `outline: none` without a replacement.
- CSS-07 Text/background contrast at least 4.5:1 (3:1 for large text); respect `prefers-reduced-motion` and `prefers-color-scheme` where relevant.
- CSS-08 Animate only `transform` and `opacity`; no layout-shifting animations.
- CSS-09 Group by component; remove unused rules when removing markup.
