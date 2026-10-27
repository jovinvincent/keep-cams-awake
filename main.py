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
    "//p[contains(., 'get this app back up')]",
]


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
            btn = wait.until(
                EC.presence_of_element_located((By.XPATH, xp))
            )
            # Scroll into view and use JS click so hidden/overlaid elements
            # can't silently swallow the click.
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'})", btn
            )
            return btn
        except TimeoutException:
            continue
    return None


def wake_app():
    attempt = 0
    while attempt < 3:
        attempt += 1
        driver = build_driver()
        try:
            print(f"[{time.strftime('%F %T')}] Opening   {APP_URL}")
            driver.get(APP_URL)

            button = find_wake_button(driver, timeout=20)
            if button is None:
                app_content = driver.find_elements(
                    By.CSS_SELECTOR,
                    "[data-testid='stAppViewContainer']",
                )
                if app_content:
                    print("App is already awake. Nothing to do.")
                    return 0
                print("Page loaded but no wake button and no app found —"
                      " the app may have been deleted or renamed.")
                return 1

            print("Sleep page found. Clicking the wake button...")
            driver.execute_script("arguments[0].click()", button)

            # The body of the progress bar / spinner is written as the
            # element tree ticks in; give the app time to actually boot.
            time.sleep(10)
            driver.refresh()
            time.sleep(5)

            again = find_wake_button(driver, timeout=10)
            if again is None:
                print("SUCCESS: app woke up.")
                return 0
            print("Wake button still shown after click (attempt"
                  f" {attempt}/3) — retrying.")

        except WebDriverException as e:
            print(f"Browser error on attempt {attempt}/3: {e}")
        finally:
            try:
                driver.quit()
            except WebDriverException:
                pass
        time.sleep(10)

    return 1


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
