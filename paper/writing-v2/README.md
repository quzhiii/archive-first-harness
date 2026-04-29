# Writing Workspace

## Files

- `draft.md` — working markdown draft
- `paper.tex` — LaTeX paper skeleton
- `references.bib` — bibliography file

## Current status

This directory now contains both a markdown-first drafting workflow and a LaTeX-first submission workflow.

Use `draft.md` for fast content iteration. Use `paper.tex` when you want to start shaping the actual submission.

## Suggested next steps

1. Replace placeholder author information in `paper.tex`
2. Decide the target conference template (EMNLP demo template vs generic article)
3. Replace figure placeholders with real figures
4. Expand bibliography entries beyond the current seed references
5. Port final wording from `draft.md` into `paper.tex` as the source of truth

## Compile hints

If you have LaTeX installed locally:

```bash
pdflatex paper.tex
bibtex paper
pdflatex paper.tex
pdflatex paper.tex
```

Or upload `paper.tex` and `references.bib` to Overleaf.

## Figure placeholders currently in `paper.tex`

- agent tooling stack / Evidence Layer positioning
- archive comparison anatomy

Both should be replaced before submission.
