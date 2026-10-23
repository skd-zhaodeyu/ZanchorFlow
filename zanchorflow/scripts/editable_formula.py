#!/usr/bin/env python3
"""Render LaTeX formulas into image assets for page manifests."""

from __future__ import annotations

import argparse
import hashlib
import os
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_ENGINE_CANDIDATES = ("xelatex", "lualatex", "pdflatex", "tectonic")
DEFAULT_TIMEOUT = 120
DEFAULT_DPI = 300
SUPPORTED_FORMATS = {"svg", "png", "pdf"}


class FormulaRenderError(RuntimeError):
    pass


def select_latex_engine(engine: str | None = None) -> str:
    if engine and engine != "auto":
        resolved = shutil.which(engine)
        if not resolved:
            raise FormulaRenderError(f"LaTeX engine not found: {engine}")
        return resolved
    for candidate in DEFAULT_ENGINE_CANDIDATES:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FormulaRenderError(
        "No LaTeX engine found. Install a TeX distribution that provides xelatex, lualatex, or pdflatex."
    )


def render_latex_asset(
    *,
    tex: str,
    out: str | Path,
    page_dir: str | Path | None = None,
    output_format: str | None = None,
    engine: str | None = None,
    preamble: str = "",
    full_document: bool = False,
    display: bool = True,
    dpi: int = DEFAULT_DPI,
    timeout: int = DEFAULT_TIMEOUT,
    shell_escape: bool = False,
    keep_workdir: str | Path | None = None,
) -> dict[str, Any]:
    if not tex.strip():
        raise FormulaRenderError("LaTeX input is empty.")
    out_path = resolve_output_path(out, page_dir)
    fmt = normalise_format(output_format, out_path)
    source_tex = out_path.with_suffix(".tex")
    source_tex.parent.mkdir(parents=True, exist_ok=True)
    document = build_latex_document(tex, preamble=preamble, full_document=full_document, display=display)
    source_tex.write_text(document, encoding="utf-8")

    resolved_engine = select_latex_engine(engine)
    if shell_escape:raise FormulaRenderError("Shell escape is not supported by editable path.")
    with tempfile.TemporaryDirectory(dir=out_path.parent,prefix="formula-work-") as tmp:
        workdir = Path(tmp)
        work_tex = workdir / "formula.tex"
        work_tex.write_text(document, encoding="utf-8")
        command = [
            resolved_engine,
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
        ]
        if shell_escape:
            command.append("-shell-escape")
        command.append(work_tex.name)
        if Path(resolved_engine).stem.lower()=='tectonic':command=[resolved_engine,'--untrusted','--keep-logs',work_tex.name]
        env=os.environ.copy();env['TECTONIC_CACHE_DIR']=str(out_path.parent/'.tex-cache');env['TEMP']=env['TMP']=str(workdir)
        result = subprocess.run(
            command,
            cwd=workdir,env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            out_path.with_suffix(".log").write_text((result.stdout or "")+"\n"+(result.stderr or ""),encoding="utf-8")
            _maybe_keep_workdir(workdir, keep_workdir)
            raise FormulaRenderError(_latex_error_message(result))
        pdf = workdir / "formula.pdf"
        if not pdf.exists():
            _maybe_keep_workdir(workdir, keep_workdir)
            raise FormulaRenderError("LaTeX completed but formula.pdf was not produced.")
        converter = convert_pdf(pdf, out_path, fmt, dpi=dpi, timeout=timeout)
        _maybe_keep_workdir(workdir, keep_workdir)
    return {
        "out": str(out_path),
        "format": fmt,
        "tex_source": str(source_tex),
        "engine": Path(resolved_engine).name,
        "converter": converter,
    }


def build_latex_document(tex: str, *, preamble: str = "", full_document: bool = False, display: bool = True) -> str:
    if full_document:
        return tex if tex.endswith("\n") else tex + "\n"
    body = tex.strip()
    if display:
        body = "$\\displaystyle\n" + body + "\n$"
    else:
        body = "$" + body + "$"
    return (
        "\\documentclass[border=2pt]{standalone}\n"
        "\\usepackage{amsmath,amssymb,mathtools,bm}\n"
        "\\usepackage{xcolor}\n"
        f"{preamble.strip()}\n"
        "\\begin{document}\n"
        f"{body}\n"
        "\\end{document}\n"
    )


def convert_pdf(pdf: Path, out_path: Path, fmt: str, *, dpi: int, timeout: int) -> str:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "pdf":
        shutil.copy2(pdf, out_path)
        return "copy-pdf"
    if fmt in ('svg','png'):
        try:import fitz
        except ImportError:raise FormulaRenderError('PyMuPDF is required for SVG/PNG conversion.')
        with fitz.open(pdf) as doc:
            if len(doc)!=1:raise FormulaRenderError('Formula must render to one page.')
            page=doc[0]
            if fmt=='svg':out_path.write_text(page.get_svg_image(text_as_path=True),encoding='utf-8')
            else:
                from PIL import Image
                pix=page.get_pixmap(matrix=fitz.Matrix(dpi/72,dpi/72),alpha=True)
                image=Image.frombytes('RGBA',[pix.width,pix.height],pix.samples);bounds=image.getchannel('A').getbbox()
                if bounds is None:raise FormulaRenderError('Formula has no visible output.')
                image.crop(bounds).save(out_path)
        return 'PyMuPDF'
    raise FormulaRenderError(f"Unsupported formula output format: {fmt}")


def formula_image_fragment(
    *,
    formula_id: str,
    image_path: str | Path,
    tex_source: str | Path,
    box_px: str | list[Any],
    page_dir: str | Path | None = None,
    z_index: int = 220,
    alt: str | None = None,
) -> dict[str, Any]:
    path_for_manifest = manifest_path(image_path, page_dir)
    tex_for_manifest = manifest_path(tex_source, page_dir)
    return {
        "schema_version": 1,
        "type": "latex-formula-image-fragment",
        "images": [
            {
                "id": formula_id,
                "path": path_for_manifest,
                "box_px": parse_box_px(box_px),
                "alt": alt or f"LaTeX rendered formula {formula_id}",
                "z_index": z_index,
            }
        ],
        "asset_provenance": [
            {
                "path": path_for_manifest,
                "source": tex_for_manifest,
                "source_type": "latex-rendered-formula",
                "provenance_note": "Rendered from LaTeX by editppt formula render-latex; visual fidelity is prioritized over formula editability.",
            }
        ],
        "formula_inventory": [
            {
                "id": formula_id,
                "decision": "latex-rendered-image",
                "editable": False,
                "image": path_for_manifest,
                "tex_source": tex_for_manifest,
            }
        ],
    }


def write_json(payload: dict[str, Any], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_output_path(out: str | Path, page_dir: str | Path | None = None) -> Path:
    path = Path(out)
    if not path.is_absolute() and page_dir:
        path = Path(page_dir) / path
    return path.resolve()


def normalise_format(output_format: str | None, out_path: Path) -> str:
    fmt = (output_format or out_path.suffix.lstrip(".") or "svg").lower()
    if fmt == "jpg":
        fmt = "jpeg"
    if fmt not in SUPPORTED_FORMATS:
        raise FormulaRenderError(f"Unsupported formula output format: {fmt}. Use svg, png, or pdf.")
    return fmt


def parse_box_px(value: str | list[Any]) -> list[float]:
    parts = [part.strip() for part in value.split(",")] if isinstance(value, str) else list(value)
    if len(parts) != 4:
        raise FormulaRenderError("box_px must be x,y,width,height")
    return [float(part) for part in parts]


def manifest_path(path: str | Path, page_dir: str | Path | None = None) -> str:
    resolved = Path(path).resolve()
    if page_dir:
        root = Path(page_dir).resolve()
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError:
            pass
    return resolved.as_posix()


def _run_converter(command: list[str], timeout: int) -> None:
    result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    if result.returncode != 0:
        raise FormulaRenderError(
            "Formula conversion failed: "
            + " ".join(command)
            + "\n"
            + "\n".join((result.stderr or result.stdout or "").splitlines()[-20:])
        )


def _latex_error_message(result: subprocess.CompletedProcess[str]) -> str:
    log = (result.stdout or "")+"\n"+(result.stderr or "")
    tail = "\n".join(log.splitlines()[-30:])
    return f"LaTeX render failed with exit code {result.returncode}.\n{tail}"


def _maybe_keep_workdir(workdir: Path, keep_workdir: str | Path | None) -> None:
    if not keep_workdir:
        return
    target = Path(keep_workdir)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(workdir, target)


def main():
    p=argparse.ArgumentParser(description='Render complete LaTeX formula assets locally; keep TeX source.')
    p.add_argument('--tex',required=True,help='UTF-8 TeX body file');p.add_argument('--output',required=True);p.add_argument('--engine');p.add_argument('--full-document',action='store_true');p.add_argument('--timeout',type=int,default=120)
    a=p.parse_args()
    try:
        result=render_latex_asset(tex=Path(a.tex).read_text(encoding='utf-8'),out=a.output,engine=a.engine,full_document=a.full_document,timeout=a.timeout)
        result.update(status='RENDERED_NOT_VISUALLY_ASSESSED',sha256=hashlib.sha256(Path(a.output).read_bytes()).hexdigest(),tex_sha256=hashlib.sha256(Path(result['tex_source']).read_bytes()).hexdigest())
    except (OSError,RuntimeError,subprocess.SubprocessError) as exc:result={'status':'BLOCKED_FORMULA_RENDER','detail':str(exc),'preserve_source':True}
    print(json.dumps(result,ensure_ascii=False,indent=2));return int(result['status']=='BLOCKED_FORMULA_RENDER')

if __name__=='__main__':raise SystemExit(main())
