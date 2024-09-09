from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import base64
import os

def ui_analyzer(url: str, viewport_width: int = 1920, viewport_height: int = 1080) -> dict:
    """
    Analyze UI by taking a screenshot of the given URL and returning the HTML and encoded image.

    Args:
        url (str): The URL of the webpage to analyze.
        viewport_width (int): The width of the viewport (default 1920).
        viewport_height (int): The height of the viewport (default 1080).

    Returns:
        dict: A dictionary containing the page title, HTML, and base64 encoded screenshot.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument(f"--window-size={viewport_width},{viewport_height}")

    try:
        with webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options) as driver:
            driver.get(url)

            # Get page title and HTML
            page_title = driver.title
            page_html = driver.page_source

            # Take screenshot
            screenshot_path = "screenshot.png"
            driver.save_screenshot(screenshot_path)

            # Encode screenshot to base64
            with open(screenshot_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

            # Clean up the screenshot file
            os.remove(screenshot_path)

        return {
            "title": page_title,
            "html": page_html,
            "screenshot": encoded_image
        }

    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}

output = ui_analyzer('http://localhost:58738/1/rendered-component')

print('output', output)