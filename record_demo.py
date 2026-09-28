import asyncio
import glob
import os
import subprocess
from playwright.async_api import async_playwright
import imageio_ffmpeg

APP_URL = "https://wanderlust-ai-frontend-1072966491314.us-east1.run.app"
RAW_DIR = "/tmp/demo_raw"
FINAL_VIDEO = "/config/antigravity/wise-curie/wanderlust-ai-demo.mp4"
AUDIO_FILE = "/tmp/lofi_beat.wav"

async def record():
    os.makedirs(RAW_DIR, exist_ok=True)
    for f in glob.glob(os.path.join(RAW_DIR, "*")):
        try:
            os.remove(f)
        except Exception:
            pass

    async with async_playwright() as p:
        print("Launching Chromium browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=RAW_DIR,
            record_video_size={"width": 1280, "height": 720}
        )
        page = await context.new_page()
        
        print("Navigating to Wanderlust AI app...")
        await page.goto(APP_URL, wait_until="networkidle")
        await page.wait_for_timeout(2500)
        
        # 1. First Prompt: Click the Kyoto example prompt chip
        print("1. Clicking Prompt Chip 1 (Kyoto Trip + Image)...")
        chips = page.locator(".prompt-chip")
        await chips.nth(0).click()
        
        print("Waiting for agent A2UI response for Prompt 1...")
        await page.wait_for_selector(".msg.agent", timeout=45000)
        await page.wait_for_function("document.querySelector('.msg.agent .bubble')?.textContent !== '…'", timeout=45000)
        await page.wait_for_timeout(7000) # Pause so viewer can see the card and postcard image
        
        # 2. Second Prompt: Rich database lookup + budget split prompt
        print("2. Typing Prompt 2 (Paris Catalog Lookup & Budget Split)...")
        prompt2_text = "Look up Paris in our catalog and estimate a $1,500 budget split for 3 travelers"
        await page.fill("#input", prompt2_text)
        await page.wait_for_timeout(1200)
        await page.click(".send-btn")
        
        print("Waiting for agent response for Prompt 2...")
        await page.wait_for_function("document.querySelectorAll('.msg.agent').length >= 2", timeout=45000)
        await page.wait_for_function("document.querySelectorAll('.msg.agent')[1]?.querySelector('.bubble')?.textContent !== '…'", timeout=45000)
        await page.wait_for_timeout(8000) # Pause so viewer can appreciate the database lookup & budget output
        
        print("Closing browser context...")
        await page.close()
        await context.close()
        await browser.close()

def merge_audio():
    video_files = glob.glob(os.path.join(RAW_DIR, "*.webm")) + glob.glob(os.path.join(RAW_DIR, "*.mp4"))
    if not video_files:
        raise Exception("No recorded video file found in RAW_DIR")
    
    raw_video = video_files[0]
    print(f"Recorded raw video file: {raw_video}")
    
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", raw_video,
        "-i", AUDIO_FILE,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        FINAL_VIDEO
    ]
    print("Executing ffmpeg:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"Successfully generated final demo video at: {FINAL_VIDEO}")

if __name__ == "__main__":
    asyncio.run(record())
    merge_audio()
