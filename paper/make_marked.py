"""Regenerate paper_dtrap_marked.tex from paper_dtrap.tex.

The journal asks that changes since the original submission be highlighted
("using bold or colored text"). Rather than hand-maintaining a second copy, this
re-derives the marked version from the clean one, so the two cannot drift.

Two kinds of mark:
  * BLOCKS  - sections written or rewritten wholesale, wrapped in a colour group
  * INLINE  - individual rewritten sentences / table cells, wrapped in \\rev{}

Anchors are matched exactly; anything that fails to match is reported rather
than silently skipped, so a reworded passage cannot quietly lose its marking.
"""
import re, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "paper_dtrap.tex")
DST = os.path.join(HERE, "paper_dtrap_marked.tex")

PREAMBLE = r"""\usepackage{xcolor}
\definecolor{revblue}{RGB}{0,64,170}
%% Revision markers: text in revblue is new or rewritten since the original
%% submission (COL-26-0021). Unmarked text is unchanged.
\newcommand{\rev}[1]{\textcolor{revblue}{#1}}

\setcopyright{none}"""

# (start-pattern, end-lookaround) for wholesale-rewritten regions
BLOCKS = [
    (r'\\section\{Methods\}', r'(?=\\section\{Experimental Results\})'),
    (r'\\subsection\{The Capture Threshold Transfers to LLMs \(RQ3\)\}',
     r'(?<=\\label\{fig:pc\}\n\\end\{figure\}\n)'),
    (r'\\subsection\{The Capability Gate is a Floor, Not a Scale Curve \(RQ2\)\}',
     r'(?=\\subsection\{)'),
    (r'\\subsection\{Only a Constrained Verifier Can Realize the Ceiling\}',
     r'(?<=\\label\{fig:verif\}\n\\end\{figure\}\n)'),
    (r'\\subsection\{Cooperation: Institutions, Not Fractions \(RQ2, RQ3\)\}',
     r'(?<=\\label\{fig:govsim\}\n\\end\{figure\}\n)'),
    (r'\\section\*\{Appendix B: Prompt Templates and Parameters\}',
     r'(?=\\bibliographystyle)'),
]

# passages rewritten in place; (open_anchor, close_anchor) -- close may be None
# to wrap a single self-contained string
INLINE = [
    # abstract
    ("we show that sufficiently capable models reproduce the tipping point at $p_c = 0.0959", None,
     "statistically indistinguishable from the analytic value $0.0979$"),
    ("The transition is \\emph{capability-gated}, but the gate is a floor", None,
     "so parameter count is a poor proxy for fitness to govern."),
    ("The capture threshold does \\emph{not} generalize to cooperation", None,
     "we show that any threshold quoted without its observation horizon overstates robustness."),
    # contributions
    ("\\item \\textbf{Fitness to govern is a capability floor, not a scale curve.}", None,
     "so an admission rule stated as a parameter count is wrong in both directions. (RQ2)"),
    ("and (ii) an institutional ladder for commons cooperation", None,
     "rather than by the adversary's share."),
    # implications
    ("Participation in governance structures should be restricted based on demonstrable capabilities, but \\emph{not} by parameter count.", None,
     "re-run as the fleet is updated."),
    ("A coordinated minority of approximately $10\\%$ can reverse an opinion-formation process", None,
     "but \\emph{false comfort} for a commons."),
    # conclusion
    ("The capture threshold observed in human social systems transfers to LLM-based societies for opinion formation", None,
     "rather than by the adversary's share."),
]

# table rows: colour each cell so the & separators stay outside the macro
ROW_KEYS = ["Tipping transfers to LLMs", "Capability gate", "Cooperation &",
            "Calibrated verifiers", "Below the capability floor",
            "Verifiable task \\emph{with} a \\emph{constrained} verifier"]


def main():
    s = open(SRC, encoding="utf-8").read()
    s = s.replace("\\setcopyright{none}", PREAMBLE, 1)
    problems = []

    for start, end in BLOCKS:
        m = re.search(start + r".*?" + end, s, re.S)
        if not m:
            problems.append(f"BLOCK not found: {start[:60]}")
            continue
        s = s[:m.start()] + "{\\color{revblue}%\n" + m.group(0).rstrip() + "\n}%\n" + s[m.end():]

    for open_a, _, close_a in INLINE:
        i = s.find(open_a)
        j = s.find(close_a, i + len(open_a)) if i >= 0 else -1
        if i < 0 or j < 0:
            problems.append(f"INLINE not found: {open_a[:60]}")
            continue
        end = j + len(close_a)
        s = s[:i] + "\\rev{" + s[i:end] + "}" + s[end:]

    for key in ROW_KEYS:
        m = re.search(r"^" + re.escape(key) + r".*?\\\\$", s, re.M)
        if not m:
            problems.append(f"ROW not found: {key[:50]}")
            continue
        row = m.group(0)
        cells = row[:-2].split("&")
        marked = " & ".join("\\rev{" + c.strip() + "}" for c in cells) + " \\\\"
        s = s[:m.start()] + marked + s[m.end():]

    open(DST, "w", encoding="utf-8").write(s)
    nb = s.count("color{revblue}") - 1
    print(f"wrote {os.path.basename(DST)}: {nb} block regions, {s.count(chr(92)+'rev{')} inline marks")
    if problems:
        print(f"\n!! {len(problems)} anchor(s) did not match -- those passages are UNMARKED:")
        for p in problems:
            print("   -", p)
        sys.exit(1)
    print("all anchors matched")


if __name__ == "__main__":
    main()
