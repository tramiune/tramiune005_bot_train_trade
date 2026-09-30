import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        # Launch browser and record video to scratch directory
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(record_video_dir="/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/scratch/")
        
        page = await context.new_page()
        
        print("Navigating to CoinMarketCap...")
        await page.goto("https://coinmarketcap.com/")
        await page.wait_for_timeout(2000)
        
        print("Clicking on Search...")
        # Try to find the search input or button
        search_button = page.locator('.search-input-box')
        if await search_button.count() > 0:
            await search_button.click()
        else:
            await page.click('text="Search"')
        
        await page.wait_for_timeout(1000)
        
        print("Typing XRP...")
        await page.keyboard.type("XRP")
        await page.wait_for_timeout(2000)
        
        print("Pressing Enter...")
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(4000)
        
        print("Taking a look at the chart...")
        # Scroll down slightly to view the chart
        await page.mouse.wheel(0, 500)
        await page.wait_for_timeout(3000)
        
        # Close context to ensure video is saved
        print("Closing and saving video...")
        await context.close()
        await browser.close()

asyncio.run(run())
