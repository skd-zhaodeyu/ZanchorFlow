# Third-party code

editable_geometry.py derives from ningzimu/image-to-editable-ppt-skill, commit b7be494e31a0ed56ef98716891db5474606b8cdf, cli/editppt/runtime/path_geometry.py. Source retained unchanged.

MIT License

Copyright (c) 2026 ningzimu

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Additional adapted modules from the same pinned MIT source: page_text_metrics.py, text_hints.py, paddle_text_hints.py, remove_chroma_key.py and split_alpha_components.py. They are named editable_*.py locally. Changes: local imports and Windows font discovery, optional explicit OCR upload, environment-only credentials, and redacted provider errors. Geometry and alpha ownership algorithms retain upstream semantics.

editable_formula.py adapts formula_renderer.py from the same pinned MIT source: project-local temporary/cache directories, optional portable Tectonic, shell escape disabled, and PyMuPDF SVG/PNG conversion.

Further chroma adaptation preserves pre-existing faint non-key foreground alpha; the noise-floor cleanup applies only to alpha newly derived from fully opaque pixels. Formula display math uses an LR-box-compatible standalone wrapper, verified with portable Tectonic.
