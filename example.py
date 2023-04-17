import requests
import asyncio
import cv2
import numpy as np

from playwright.async_api import PlaywrightContextManager
from playwright_stealth import StealthConfig, stealth_async
from python_ghost_cursor.playwright_async import create_cursor


"""
    Captcha solver stuff
"""
def slide_captcha(): # captcha with slide image
    try:
        inner_circle = cv2.imread('image_2.jpg')

        # Konvertiere es zu Graustufen
        gray = cv2.cvtColor(inner_circle, cv2.COLOR_BGR2GRAY)

        # Finde die Kreiskontur des inneren Kreises
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, 20, param1=50, param2=30, minRadius=0, maxRadius=0)

        # Extrahiere die Koordinaten des Kreismittelpunkts
        x, y, r = np.round(circles[0][0]).astype("int")

        # Berechne den Grad der Rotation
        template = cv2.imread('image_1.jpg', 0)
        result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        angle = np.degrees(np.arctan2(max_loc[1] - y, max_loc[0] - x))

        pix = 0.65

        if "-" in str(angle):
            angle = abs(angle)
        pix_slide = pix * angle

        #os.remove("image_1.jpg")
        #os.remove("image_2.jpg")

        # lower or higher this, can improve the solving, 
        # I already tested 0.5 to 2.3 but somehow it sometimes works better and sometimes it needs a long time to solve
        return pix_slide*2.1
    except:
        print("Error with captcha solver")

async def download_image(page, selector, name):
    # Find the element with the specified selector
    src = await page.evaluate("(selector) => document.querySelector(selector).getAttribute('src')", selector)
    # Download the image using the requests library
    response = requests.get(src)
    if response.status_code == 200:
        with open(f"{name}.jpg", "wb") as f:
            f.write(response.content)


async def solve_slide_captcha(page):
    cursor = create_cursor(page)
    element = await page.query_selector("#secsdk-captcha-drag-wrapper > div.secsdk-captcha-drag-icon.sc-kEYyzF.fiQtnm > div")
    bb = await element.bounding_box()
    x = bb["x"]
    y = bb["y"]
    print(f"Element is located at ({x}, {y})")

    await download_image(page, "#captcha_container > div > div.sc-jTzLTM.kuTGKN > img.sc-fjdhpX.jPkBzC", "image_1")
    await download_image(page, "#captcha_container > div > div.sc-jTzLTM.kuTGKN > img.sc-cSHVUG.kckaJv", "image_2")
    move_to = slide_captcha()
    await cursor.move_to({"x": 490,"y": 498.015625})
    #await page.mouse.move(493.015625, 498.015625)#
    await page.mouse.down()
    await cursor.move_to({"x": 490+move_to,"y": 498.015625})
    #await page.mouse.move(493.015625+move_to, 498.015625, steps=100)#
    await page.mouse.up()

    await asyncio.sleep(3)
    return



"""
    Playwright/Main stuff
"""
async def catch_login_info(response, queue, url: str):
    try:
        if url in response.url:
            result = await response.json()

            await queue.put(result)
            email = result["data"]["email"]
            print(f"Logged in with email: {email}")
    except:
        pass

async def example(email, password):
    playwright = await PlaywrightContextManager().start()

    params = {
        "headless": False,
        "args": [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-web-security",
            "--disable-notifications",
        ],
    }

    browser = await playwright.chromium.launch(**params)
    context = await browser.new_context()
    page = await context.new_page()

    # set stealth mode for tiktok
    await stealth_async(
        page,
        StealthConfig(
            webdriver=True,
            webgl_vendor=True,
            chrome_app=False,
            chrome_csi=False,
            chrome_load_times=False,
            chrome_runtime=False,
            iframe_content_window=True,
            media_codecs=True,
            navigator_hardware_concurrency=4,
            navigator_languages=False,
            navigator_permissions=True,
            navigator_platform=False,
            navigator_plugins=True,
            navigator_user_agent=False,
            navigator_vendor=False,
            outerdimensions=True,
            hairline=False,
        ),
    )


    await page.goto("https://www.tiktok.com/login/phone-or-email/email", page, wait_until="networkidle")

    try:
        # accept cookies
        await page.wait_for_selector("div > div.button-wrapper > button:nth-child(2)", timeout=1000)
        await page.click("div > div.button-wrapper > button:nth-child(2)")
    except:
        pass

    # input email
    await page.wait_for_selector("#loginContainer > div.tiktok-xabtqf-DivLoginContainer.exd0a430 > form > div.tiktok-q83gm2-DivInputContainer.etcs7ny0 > input")
    await page.type("#loginContainer > div.tiktok-xabtqf-DivLoginContainer.exd0a430 > form > div.tiktok-q83gm2-DivInputContainer.etcs7ny0 > input", email, delay=0.3)
    
    await asyncio.sleep(1)

    # input password
    await page.type("#loginContainer > div.tiktok-xabtqf-DivLoginContainer.exd0a430 > form > div.tiktok-15iauzg-DivContainer.e1bi0g3c0 > div > input", password, delay=0.3)

    await asyncio.sleep(1)

    await page.click("#loginContainer > div.tiktok-xabtqf-DivLoginContainer.exd0a430 > form > button")

    await asyncio.sleep(3)

    try:
        await page.wait_for_selector("#loginContainer > div.tiktok-xabtqf-DivLoginContainer.exd0a430 > form > div.tiktok-3i0bsv-DivTextContainer.e3v3zbj0", timeout=1000)
        print("Try again later -> sleeping 5 mins and retry")
        await asyncio.sleep(60*5)
        await page.click("#loginContainer > div.tiktok-xabtqf-DivLoginContainer.exd0a430 > form > button")
    except:
        pass

    login_info_queue: asyncio.Queue = asyncio.Queue(maxsize=1)

    page.on(
        "response",
        lambda res: asyncio.create_task(catch_login_info(res, login_info_queue, "/user/login")),
    )

    x = await page.is_visible("#captcha_container > div > div.captcha_verify_slide--button.slide-button___StyledDiv-sc-11qn0r0-0.kXElFp", timeout=1000)
    while x == True:
        await asyncio.sleep(3)
        await solve_slide_captcha(page)

    await page.wait_for_selector('div[data-e2e="profile-icon"]', timeout=0)

    # You can save your cookies and reuse them so you bypass login captcha
    cookies = await page.context.cookies()

    await context.close()
