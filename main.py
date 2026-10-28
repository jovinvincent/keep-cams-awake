import os
import sys
import time
import argparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Your Streamlit app URL (can be overridden with the APP_URL env var)
APP_URL = os.environ.get(
    "APP_URL",
    "https://cams-converter-gcbzwwtgvm42gszgjauowt.streamlit.app/",
)

# XPath matches the label text even when Streamlit nests it in a <p> inside
# the <button> — the old "contains(text(),...)" only matched direct text nodes
# and never found the button.
WAKE_BUTTON_XPATHS = [
    "//button[contains(., 'get this app back up')]",
    "//button[contains(., 'Yes') and contains(., 'back up')]",
]

# A live Streamlit page for this particular app must show its app-specific UI,
# not merely the generic Streamlit container (which can also exist on shell pages).
LIVE_APP_TEXT = "CAMS CAS"
FILE_UPLOADER_SELECTOR = "[data-testid='stFileUploader']"


def app_is_ready(driver):
    """Return True only after the actual CAMS converter UI is rendered."""
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        has_app_text = LIVE_APP_TEXT.lower() in body_text.lower()
        has_uploader = bool(driver.find_elements(By.CSS_SELECTOR, FILE_UPLOADER_SELECTOR))
        return has_app_text and has_uploader
    except WebDriverException:
        return False



def build_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=options)


def find_wake_button(driver, timeout=30):
    """Return the sleep/wake button if present, else None."""
    wait = WebDriverWait(driver, timeout)
    for xp in WAKE_BUTTON_XPATHS:
        try:
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'})", btn
            )
            return btn
        except TimeoutException:
            continue
    return None


def wait_until_app_ready(driver, timeout=150):
    """Wait for the real CAMS converter UI after Streamlit starts."""
    try:
        WebDriverWait(driver, timeout, poll_frequency=2).until(app_is_ready)
        return True
    except TimeoutException:
        return False


def wake_app():
    driver = None
    try:
        driver = build_driver()
        print(f"[{time.strftime('%F %T')}] Opening {APP_URL}", flush=True)
        driver.set_page_load_timeout(90)
        driver.get(APP_URL)

        if app_is_ready(driver):
            print("SUCCESS: CAMS converter UI is already live.", flush=True)
            return 0

        button = find_wake_button(driver, timeout=25)
        if button is None:
            print(
                "ERROR: Neither the CAMS converter UI nor the Streamlit wake button "
                "was found. Page title: " + driver.title,
                flush=True,
            )
            return 1

        print("Sleeping page detected. Clicking the wake button...", flush=True)
        try:
            button.click()
        except WebDriverException:
            # Fallback for Streamlit's nested/overlaid button markup.
            driver.execute_script("arguments[0].click()", button)

        # Do not refresh while Streamlit is still starting. Wait for the actual
        # app-specific title and uploader to appear.
        if wait_until_app_ready(driver, timeout=180):
            print("SUCCESS: CAMS converter is awake and its UI is ready.", flush=True)
            return 0

        print(
            "ERROR: Wake button was clicked, but CAMS converter UI did not become "
            "ready within 180 seconds. This run is marked failed.",
            flush=True,
        )
        return 1

    except (TimeoutException, WebDriverException) as e:
        print(f"ERROR: Browser/wake attempt failed: {type(e).__name__}: {e}", flush=True)
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected wake failure: {type(e).__name__}: {e}", flush=True)
        return 1
    finally:
        if driver is not None:
            try:
                driver.quit()
            except WebDriverException:
                pass


def keep_awake(interval_hours=6.0, once=False):
    if once:
        return wake_app()
    print(f"Loop mode: waking the app every {interval_hours} h. Ctrl+C stops.")
    while True:
        try:
            wake_app()
        except Exception as e:
            print(f"Unexpected error: {e}")
        time.sleep(interval_hours * 3600)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Keep a Streamlit app awake")
    parser.add_argument("--once", action="store_true",
                        help="Run once and exit (old behaviour)")
    parser.add_argument("--interval", type=float, default=6.0,
                        metavar="HOURS",
                        help="Hours between wakes in loop mode (default 6)")
    args = parser.parse_args()
    sys.exit(keep_awake(interval_hours=args.interval, once=args.once))
