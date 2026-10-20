# jackraney.com

Personal site of Jack Raney. Plain HTML, CSS and JavaScript with no build step, served by GitHub Pages.

- The `.html` files in this folder are the pages. `404.html` is the not-found page.
- `assets/css/site.css` is the only stylesheet. `assets/js/site.js` handles the light and dark theme.
- `assets/js/hours.js` draws the grid of every hour of 2025 on the calculator and the memo.
- `assets/js/calculator.js` runs the ERCOT power cost calculator on `assets/data/ercot-2025.js`, which holds ERCOT's 2025 real-time hub prices (report NP6-785-ER) averaged from 15-minute intervals to hours.
- `resume/Jack-Raney-Resume.pdf` is printed from `resume.html`.
- `downloads/power-cost-model-sample.xlsx` is a sample model built on made-up numbers.

## Numbers that change (data/facts.json)

Numbers that appear in several places (Archibald runs, success rate, skills, live jobs, Otian paying clients, the footer "Updated" month) live in `data/facts.json`. Pages mark them with `<span data-fact="key">…</span>`.

To update one: edit the value in `data/facts.json` and run `python3 scripts/build_facts.py` (the publish workflow also runs it). If `resume.html` changed, `python3 scripts/build_resume_pdf.py` rebuilds the one-page PDF, and keeps the old one if the new version would run past one page.
