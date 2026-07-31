from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time

# Your Streamlit app URL
APP_URL = "https://cams-converter-gcbzwwtgvm42gszgjauowt.streamlit.app/"

def wake_app():
    print("Starting browser...")

    # Set up Chrome to run without a real screen (headless)
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)

    try:
        print(f"Opening your app: {APP_URL}")
        driver.get(APP_URL)

        # Wait up to 20 seconds for the page to load
        wait = WebDriverWait(driver, 20)

        try:
            # Look for the blue "Yes, get this app back up!" button
            button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Yes, get this app back up')]"))
            )
            print("Found the sleep button! Clicking it now...")
            button.click()

            # Wait a few seconds for the app to wake up
            time.sleep(5)
            print("App is waking up! Done.")

        except TimeoutException:
            print("No sleep button found. Your app is already awake. Done.")

    except Exception as e:
        print(f"Something went wrong: {e}")
        return 1

    finally:
        driver.quit()

    return 0

if __name__ == "__main__":
    wake_app()
