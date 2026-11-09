// Smartist LLC Document Template
// Version: 1.3.0 (Bergfink-inspired)
//
// 1.3.0, 12.09.2026 — базовый кегль 11pt → 12pt и производные по всей вёрстке.
// Причина: документы читают с телефона, 11pt на A4 в мобильной читалке мелковат.
// Supports: Russian, Emojis, Title page, Headers/Footers, Striped tables
//
// Имена шрифтов лежат не здесь, а в пакете @local/fonts: он свой на каждой ОС
// (fonts-macos.typ / fonts-linux.typ, выбирает раскатка). Вёрстка ниже общая.

#import "@local/fonts:1.0.0": sans, mono

#let smartist(
  title: none,
  subtitle: none,
  author: "Smartist LLC",
  date: none,
  titlepage: false,
  titlepage-bg: rgb("#3C78D8"),
  titlepage-fg: white,
  body
) = {
  // Document metadata
  set document(title: title, author: author)

  // Base font settings
  let fontsize = 12pt
  let leading = 0.65em
  let font = sans
  let heading-color = rgb("#282828")

  // Table styling - striped rows like Eisvogel
  let table-stroke = (_, y) => (
    left: 0pt,
    right: 0pt,
    top: if y < 1 { stroke(1pt + luma(120)) } else if y == 1 { none } else { 0pt },
    bottom: if y < 1 { stroke(0.5pt + luma(120)) } else { stroke(1pt + luma(120)) },
  )

  let striped = (x, y) => {
    if calc.even(y) and y > 0 {
      luma(245)
    } else {
      none
    }
  }

  // Header helper
  let make-header() = context {
    if counter(page).get().first() > 1 or not titlepage {
      set text(size: 10pt, fill: rgb("#555555"))
      grid(
        columns: (1fr, auto, 1fr),
        align: (left, center, right),
        if title != none { title } else { "" },
        "",
        if date != none { date } else { "" },
      )
      v(-0.5em)
      line(length: 100%, stroke: 0.75pt + luma(120))
    }
  }

  // Footer helper
  let make-footer() = context {
    set text(size: 10pt, fill: rgb("#555555"))
    line(length: 100%, stroke: 0.75pt + luma(120))
    v(-0.3em)
    grid(
      columns: (1fr, auto, 1fr),
      align: (left, center, right),
      if author != none { author } else { "" },
      "",
      counter(page).display("1"),
    )
  }

  // Page settings
  set page(
    paper: "a4",
    margin: (x: 2.5cm, top: 3cm, bottom: 2.5cm),
    header: make-header(),
    footer: make-footer(),
  )

  // Text settings
  set text(
    font: font,
    size: fontsize,
    lang: "ru",
  )

  // Paragraph settings
  set par(
    justify: true,
    leading: leading,
    spacing: 1.2em,
  )

  // Heading styles (Bergfink proportions)
  set heading(numbering: none)
  show heading: set text(font: font, fill: heading-color)

  show heading.where(level: 1): it => {
    set text(size: fontsize * 1.4, weight: "bold")
    v(1.5em)
    it
    v(0.8em)
  }

  show heading.where(level: 2): it => {
    set text(size: fontsize * 1.2, weight: "bold")
    v(1.2em)
    it
    v(0.6em)
  }

  show heading.where(level: 3): it => {
    set text(size: fontsize * 1.05, weight: "bold")
    v(1em)
    it
    v(0.4em)
  }

  // Link styling
  show link: it => {
    set text(fill: rgb("#0366d6"))
    underline(it)
  }

  // Code block styling (Bergfink style)
  show raw.where(block: true): it => {
    set text(font: mono, size: 10pt)
    block(
      fill: gray.lighten(92%),
      stroke: 0.5pt + gray,
      inset: 10pt,
      radius: 3pt,
      width: 100%,
      it
    )
  }

  // Inline code
  show raw.where(block: false): it => {
    set text(font: mono, size: 10pt)
    box(
      fill: rgb("#f5f5f5"),
      inset: (x: 3pt, y: 1pt),
      radius: 2pt,
      it
    )
  }

  // Blockquote styling
  show quote: it => {
    block(
      inset: (left: 1em, y: 0.5em),
      stroke: (left: 3pt + rgb("#dddddd")),
      text(fill: rgb("#666666"), it.body)
    )
  }

  // Table styling - striped like Eisvogel
  set table(
    stroke: table-stroke,
    fill: striped,
    inset: 8pt,
  )
  show table: set par(justify: false)
  show table: set text(size: 11pt)

  // Figure styling
  show figure: set block(above: 1.5em, below: 1.5em, breakable: true)
  show figure.where(kind: table): set figure.caption(position: top)
  show figure.where(kind: image): set figure.caption(position: bottom)
  show figure.caption: set align(left)
  show figure.caption: set text(size: 11pt, fill: rgb("#555555"))

  // Remove figure wrapper for tables from pandoc
  show figure.where(kind: table): it => {
    it.body
  }

  // List styling
  set list(indent: 1em, marker: [•])
  set enum(indent: 1em)

  // Definition list styling
  show terms: it => {
    it
      .children
      .map(child => [
        #strong[#child.term]
        #block(inset: (left: 1.5em))[#child.description]
      ])
      .join()
  }

  // Horizontal rule (centered, shorter)
  let horizontalrule = align(center, line(length: 50%, stroke: 0.5pt + luma(180)))

  // Title page
  if titlepage {
    page(
      header: none,
      footer: none,
      fill: titlepage-bg,
      margin: (left: 5cm, rest: 2.5cm),
    )[
      #set text(fill: titlepage-fg)
      #line(length: 100% + 2.5cm, stroke: 2.5pt + titlepage-fg)

      #if title != none [
        #v(20%)
        #text(size: 28pt, weight: "bold")[#title]
      ]

      #if subtitle != none [
        #v(0.65em)
        #text(size: 15pt)[#subtitle]
      ]

      #v(2em)
      #if author != none [
        #text(size: 13pt)[#author]
      ]

      #v(1fr)

      #if date != none [
        #text(size: 13pt)[#date]
      ]
    ]
    counter(page).update(0)
  } else {
    // Simple header without title page
    if title != none or subtitle != none or date != none {
      v(1em)
      align(center)[
        #if title != none {
          text(size: 22pt, weight: "bold", fill: heading-color)[#title]
          v(0.3em)
        }
        #if subtitle != none {
          text(size: 13pt, fill: rgb("#666666"))[#subtitle]
          v(0.3em)
        }
        #if author != none and date != none {
          text(size: 11pt, fill: rgb("#666666"))[#author #h(2em) #date]
        } else if author != none {
          text(size: 11pt, fill: rgb("#666666"))[#author]
        } else if date != none {
          text(size: 11pt, fill: rgb("#666666"))[#date]
        }
      ]
      v(0.5em)
      line(length: 100%, stroke: 0.75pt + luma(180))
      v(1.5em)
    }
  }

  // Main content
  body
}
