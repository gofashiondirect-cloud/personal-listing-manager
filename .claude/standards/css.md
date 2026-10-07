# CSS standard (sources: MDN, WCAG 2.2 AA)
- Mobile first: base styles for small screens, `min-width` media queries for larger ones.
- Use CSS custom properties for colours, spacing and fonts; no repeated magic values.
- Layout with flexbox/grid; avoid fixed heights and absolute positioning for page layout.
- Relative units (`rem`, `%`, `clamp()`) for type and spacing; never set `font-size` below 16px for body text.
- Keep specificity low: classes, not ids or long selector chains; no `!important` except to override third-party CSS.
- Visible `:focus-visible` styles; never `outline: none` without a replacement.
- Text/background contrast at least 4.5:1 (3:1 for large text); respect `prefers-reduced-motion` and `prefers-color-scheme` where relevant.
- Animate only `transform` and `opacity`; no layout-shifting animations.
- Group by component; remove unused rules when removing markup.
