# GitHub Pages microsite

The static site is in `docs/index.html` with `site.css`, `site.js`, and eight
standalone SVG figures in `docs/assets/illustrations/`. It has no CDN or build
dependency and uses relative asset paths so it works from the repository's
project Pages URL. The figures contain their own headings, equations, readable
labels and detailed accessible descriptions. Captions add context in the page.

## Publish

On the GitHub repository, open **Settings → Pages**. Under **Build and
deployment**, choose **Deploy from a branch**, branch **main**, directory
**/docs**, then **Save**. Wait for GitHub's Pages build to complete. The
repository's Pages URL will appear in that settings view. The first deployment
requires repository administration; copying the files alone does not enable
Pages. Keep `.nojekyll` inside `docs` to serve exact static assets.

## Illustrations and numerical example

All eight labeled SVG figures are included under `assets/illustrations/`.
The numerical posterior illustration in `site.js` uses the same default
matrices as `src/csfsm_guardrails/policies/default.yaml`. If the policy changes,
update the example and figures together and verify numerical agreement.

Preview locally with `python -m http.server 8000 -d docs`, then open
`http://localhost:8000`. The page has no access to real session state: its
interactive posterior widget demonstrates one local filter step. The live
guardrail runtime is linked as the Hugging Face Gradio Space.
