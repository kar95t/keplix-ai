"""Media tools: Headless Playwright video capture, FFmpeg, Edge-TTS, and Marp slides."""

import asyncio
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

from keplix.tools.registry import register_tool


@tool
def record_browser_session(
    url: str,
    output_path: str = "demo.webm",
    duration_seconds: int = 10,
) -> str:
    """Record a headless browser session of a live web page or local web app."""
    try:
        from playwright.async_api import async_playwright

        async def _record() -> None:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                out_dir = Path(output_path).parent
                out_dir.mkdir(parents=True, exist_ok=True)
                context = await browser.new_context(record_video_dir=str(out_dir))
                page = await context.new_page()
                await page.goto(url)
                await asyncio.sleep(duration_seconds)
                await context.close()
                await browser.close()

        asyncio.run(_record())
        return f"Browser recording saved to {output_path}."
    except ImportError:
        return "Playwright is not installed. Install with `uv pip install playwright` and `playwright install`."
    except Exception as e:
        return f"Failed to record browser session: {e}"


@tool
def generate_marp_presentation(
    markdown_content: str,
    output_path: str = "presentation.html",
    theme: str = "default",
) -> str:
    """Generate a Marp HTML presentation slide deck from markdown content."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    marp_header = f"""---
marp: true
theme: {theme}
paginate: true
---
"""
    full_content = marp_header + markdown_content
    target.write_text(full_content, encoding="utf-8")
    return f"Marp slide deck written to {output_path}."


@tool
def synthesize_narration(
    text: str,
    output_path: str = "narration.mp3",
    voice: str = "en-US-ChristopherNeural",
) -> str:
    """Generate spoken voiceover audio using Edge-TTS."""
    try:
        import edge_tts

        async def _synthesize() -> None:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)

        asyncio.run(_synthesize())
        return f"Narration synthesized to {output_path}."
    except ImportError:
        return "edge-tts is not installed. Install with `uv pip install edge-tts`."
    except Exception as e:
        return f"Failed to synthesize narration: {e}"


# Auto-register media tools
register_tool(scope="media")(record_browser_session)
register_tool(scope="media")(generate_marp_presentation)
register_tool(scope="media")(synthesize_narration)

