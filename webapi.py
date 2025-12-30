#!/usr/bin/env python3

import sys
import asyncio
import json
import time
from pathlib import Path

try:
    from gemini_webapi import set_log_level
    set_log_level("ERROR")
except ImportError:
    pass

def print_help():
    help_text = """Usage: webapi [OPTIONS] PROMPT

All-purpose Gemini 3 Pro client with Thinking enabled.
Uses browser cookies for authentication - no API key required.

Arguments:
  PROMPT                Text prompt for query/generation

Options:
  --file, -f FILE       Input file (MP4, PDF, PNG, JPG, etc.)
  --youtube URL         YouTube video URL to analyze
  --generate-image FILE Generate image and save to FILE
  --edit IMAGE          Edit existing image (use with --output)
  --output, -o FILE     Output file path (for image generation/editing)
  --aspect RATIO        Aspect ratio for image generation (16:9, 1:1, 4:3, 3:4)
  --show-thoughts       Display model's thinking process
  --model MODEL         Model to use (default: gemini-3.0-pro)
  --json                Output response as JSON
  --retries N           Number of retries for transient failures (default: 3)
  --timeout SECS        Client initialization timeout (default: 120)
  --help, -h            Show this help message

Examples:
  # Text query
  webapi "Explain quantum computing"

  # Analyze local video
  webapi "Summarize this video" --file video.mp4

  # Analyze YouTube video
  webapi "What are the key points?" --youtube "https://youtube.com/watch?v=..."

  # Analyze document
  webapi "Summarize this report" --file report.pdf

  # Generate image
  webapi "A sunset over mountains" --generate-image sunset.png

  # Edit image
  webapi "Make the sky purple" --edit photo.jpg --output edited.png

  # Show thinking process
  webapi "Solve this step by step: What is 15% of 240?" --show-thoughts

Model: gemini-3.0-pro (Thinking with 3 Pro)

Prerequisites:
  1. Log into gemini.google.com in Chrome
  2. pip install -r requirements.txt (or use the venv)
  3. First run on macOS will prompt for Keychain access"""
    print(help_text)

def parse_args(args):
    result = {
        "prompt": None,
        "file": None,
        "youtube": None,
        "generate_image": None,
        "edit": None,
        "output": None,
        "aspect": None,
        "show_thoughts": False,
        "model": "gemini-3.0-pro",
        "json_output": False,
        "retries": 3,
        "timeout": 120,
    }

    i = 0
    positional = []

    while i < len(args):
        arg = args[i]

        if arg in ("--help", "-h"):
            print_help()
            sys.exit(0)
        elif arg in ("--file", "-f"):
            i += 1
            if i >= len(args):
                print("Error: --file requires a path", file=sys.stderr)
                sys.exit(1)
            result["file"] = args[i]
        elif arg == "--youtube":
            i += 1
            if i >= len(args):
                print("Error: --youtube requires a URL", file=sys.stderr)
                sys.exit(1)
            result["youtube"] = args[i]
        elif arg == "--generate-image":
            i += 1
            if i >= len(args):
                print("Error: --generate-image requires an output filename", file=sys.stderr)
                sys.exit(1)
            result["generate_image"] = args[i]
        elif arg == "--edit":
            i += 1
            if i >= len(args):
                print("Error: --edit requires an input image", file=sys.stderr)
                sys.exit(1)
            result["edit"] = args[i]
        elif arg in ("--output", "-o"):
            i += 1
            if i >= len(args):
                print("Error: --output requires a filename", file=sys.stderr)
                sys.exit(1)
            result["output"] = args[i]
        elif arg == "--aspect":
            i += 1
            if i >= len(args):
                print("Error: --aspect requires a ratio", file=sys.stderr)
                sys.exit(1)
            result["aspect"] = args[i]
        elif arg == "--show-thoughts":
            result["show_thoughts"] = True
        elif arg == "--model":
            i += 1
            if i >= len(args):
                print("Error: --model requires a model name", file=sys.stderr)
                sys.exit(1)
            result["model"] = args[i]
        elif arg == "--json":
            result["json_output"] = True
        elif arg == "--retries":
            i += 1
            if i >= len(args):
                print("Error: --retries requires a number", file=sys.stderr)
                sys.exit(1)
            try:
                result["retries"] = int(args[i])
            except ValueError:
                print(f"Error: --retries must be a number, got '{args[i]}'", file=sys.stderr)
                sys.exit(1)
        elif arg == "--timeout":
            i += 1
            if i >= len(args):
                print("Error: --timeout requires seconds", file=sys.stderr)
                sys.exit(1)
            try:
                result["timeout"] = int(args[i])
            except ValueError:
                print(f"Error: --timeout must be a number, got '{args[i]}'", file=sys.stderr)
                sys.exit(1)
        elif not arg.startswith("-"):
            positional.append(arg)
        else:
            print(f"Error: Unknown option {arg}", file=sys.stderr)
            sys.exit(1)

        i += 1

    if not positional:
        print("Error: PROMPT is required", file=sys.stderr)
        print("Use --help for usage information", file=sys.stderr)
        sys.exit(1)

    result["prompt"] = " ".join(positional)
    return result

MAX_TOKENS = 60_000
CHARS_PER_TOKEN = 4
MAX_CHARS = MAX_TOKENS * CHARS_PER_TOKEN

def estimate_tokens(text):
    return len(text) // CHARS_PER_TOKEN

def is_transient_error(error_msg):
    transient_patterns = [
        "timeout",
        "connection",
        "temporarily",
        "rate limit",
        "503",
        "502",
        "500",
        "unavailable",
        "try again",
        "overloaded",
    ]
    lower_msg = error_msg.lower()
    return any(p in lower_msg for p in transient_patterns)

async def init_client_with_retry(timeout, max_retries):
    from gemini_webapi import GeminiClient

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Initializing Gemini client (attempt {attempt}/{max_retries})...", file=sys.stderr)
            client = GeminiClient()
            await client.init(timeout=timeout, auto_close=False, auto_refresh=True)
            print(f"Client initialized successfully", file=sys.stderr)
            return client
        except Exception as e:
            last_error = e
            error_msg = str(e)
            print(f"Init attempt {attempt} failed: {error_msg}", file=sys.stderr)

            if attempt < max_retries:
                if is_transient_error(error_msg):
                    backoff = min(2 ** attempt, 30)
                    print(f"Transient error, retrying in {backoff}s...", file=sys.stderr)
                    await asyncio.sleep(backoff)
                else:
                    backoff = 2
                    print(f"Retrying in {backoff}s...", file=sys.stderr)
                    await asyncio.sleep(backoff)

    raise last_error

async def generate_with_retry(client, prompt, files, model, max_retries, is_edit=False, edit_path=None):
    last_error = None
    last_response = None

    for attempt in range(1, max_retries + 1):
        try:
            if is_edit and edit_path:
                chat = client.start_chat()
                await chat.send_message("Here is an image to edit", files=[edit_path])
                edit_prompt = f"Use image generation tool to {prompt}"
                response = await chat.send_message(edit_prompt)
            elif files:
                response = await client.generate_content(prompt, files=files, model=model)
            else:
                response = await client.generate_content(prompt, model=model)

            last_response = response

            if response.text or response.images:
                await asyncio.sleep(0.5)
                return response

            if attempt < max_retries:
                print(f"Empty response on attempt {attempt}, retrying...", file=sys.stderr)
                await asyncio.sleep(1)
                continue

            return response

        except Exception as e:
            last_error = e
            error_msg = str(e)
            print(f"Generation attempt {attempt} failed: {error_msg}", file=sys.stderr)

            if attempt < max_retries and is_transient_error(error_msg):
                backoff = min(2 ** attempt, 30)
                print(f"Transient error, retrying in {backoff}s...", file=sys.stderr)
                await asyncio.sleep(backoff)
            elif attempt < max_retries:
                await asyncio.sleep(2)
            else:
                if last_response:
                    return last_response
                raise

    if last_response:
        return last_response
    raise last_error

async def wait_for_stable_images(response, settle_ms=2000, check_interval_ms=500):
    if not response.images:
        return response

    start = time.time()
    deadline = start + (settle_ms / 1000)
    image_count = len(response.images)
    stable_checks = 0
    required_stable = 3

    while time.time() < deadline:
        await asyncio.sleep(check_interval_ms / 1000)
        current_count = len(response.images) if response.images else 0
        if current_count == image_count and image_count > 0:
            stable_checks += 1
            if stable_checks >= required_stable:
                break
        else:
            image_count = current_count
            stable_checks = 0

    return response

async def run(args):
    try:
        from gemini_webapi import GeminiClient
    except ImportError:
        print("Error: gemini-webapi not installed", file=sys.stderr)
        print("Run: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

    prompt = args["prompt"]

    if len(prompt) > MAX_CHARS:
        tokens = estimate_tokens(prompt)
        print(f"Error: Prompt too large ({tokens:,} tokens, max {MAX_TOKENS:,})", file=sys.stderr)
        print("Reduce input size or split into smaller chunks.", file=sys.stderr)
        sys.exit(1)

    files = []

    if args["aspect"] and (args["generate_image"] or args["edit"]):
        prompt = f"{prompt} (aspect ratio: {args['aspect']})"

    if args["file"]:
        file_path = Path(args["file"])
        if not file_path.exists():
            print(f"Error: File not found: {args['file']}", file=sys.stderr)
            sys.exit(1)
        files.append(str(file_path.resolve()))

    edit_image_path = None
    if args["edit"]:
        edit_path = Path(args["edit"])
        if not edit_path.exists():
            print(f"Error: Image not found: {args['edit']}", file=sys.stderr)
            sys.exit(1)
        edit_image_path = str(edit_path.resolve())

    if args["youtube"]:
        prompt = f"{prompt}\n\nYouTube video: {args['youtube']}"

    if args["generate_image"] and not args["edit"]:
        prompt = f"Generate an image: {prompt}"

    model = args["model"]
    max_retries = args["retries"]
    timeout = args["timeout"]

    if args["file"] and args["file"].lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
        timeout = max(timeout, 180)
        print(f"Video file detected, using extended timeout ({timeout}s)", file=sys.stderr)

    try:
        client = await init_client_with_retry(timeout, max_retries)
    except Exception as e:
        print(f"Error initializing client after {max_retries} attempts: {e}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Troubleshooting:", file=sys.stderr)
        print("  1. Ensure you're logged into gemini.google.com in Chrome", file=sys.stderr)
        print("  2. On macOS, allow Keychain access when prompted", file=sys.stderr)
        print("  3. Try closing Chrome and reopening gemini.google.com", file=sys.stderr)
        print("  4. Clear Chrome cookies for gemini.google.com and re-login", file=sys.stderr)
        sys.exit(1)

    op_type = "image generation" if (args["generate_image"] or args["edit"]) else "query"
    print(f"Sending {op_type} to {model}...", file=sys.stderr)

    try:
        response = await generate_with_retry(
            client,
            prompt,
            files,
            model,
            max_retries,
            is_edit=bool(edit_image_path),
            edit_path=edit_image_path
        )

        if args["generate_image"] or edit_image_path:
            response = await wait_for_stable_images(response)

            if not response.images:
                print("No images generated after retries.", file=sys.stderr)
                print("", file=sys.stderr)
                if response.text:
                    print(f"Model response: {response.text}", file=sys.stderr)
                print("", file=sys.stderr)
                print("Suggestions:", file=sys.stderr)
                print("  - Try rephrasing the prompt", file=sys.stderr)
                print("  - Be more explicit about wanting an image", file=sys.stderr)
                print("  - Some content may be filtered by safety systems", file=sys.stderr)
                sys.exit(1)

            output_path = Path(args["generate_image"] or args["output"] or "generated.png")
            output_dir = output_path.parent if output_path.parent != Path(".") else Path(".")

            image = response.images[0]
            await image.save(path=str(output_dir), filename=output_path.name)

            print(f"Saved: {output_path}")

            if len(response.images) > 1:
                print(f"({len(response.images)} images generated, saved first one)", file=sys.stderr)

            if response.text and not args["json_output"]:
                print(f"\nResponse: {response.text}")
        else:
            if args["json_output"]:
                output = {
                    "text": response.text,
                    "thoughts": response.thoughts if args["show_thoughts"] else None,
                    "has_images": bool(response.images),
                    "image_count": len(response.images) if response.images else 0,
                }
                print(json.dumps(output, indent=2))
            else:
                if args["show_thoughts"] and response.thoughts:
                    print("=== Thinking ===")
                    print(response.thoughts)
                    print("\n=== Response ===")

                if response.text:
                    print(response.text)
                elif response.images:
                    print(f"(Response contains {len(response.images)} image(s) but no text)")
                else:
                    print("(empty response)")

    except Exception as e:
        error_msg = str(e)
        print(f"Error: {error_msg}", file=sys.stderr)
        if "cookie" in error_msg.lower() or "auth" in error_msg.lower():
            print("", file=sys.stderr)
            print("This appears to be an authentication issue.", file=sys.stderr)
            print("Try logging into gemini.google.com again in Chrome.", file=sys.stderr)
        sys.exit(1)
    finally:
        try:
            await client.close()
        except Exception:
            pass

def main():
    args = parse_args(sys.argv[1:])
    asyncio.run(run(args))

if __name__ == "__main__":
    main()
