from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from app.config import settings
from app.utils import *  # noqa: F403
from app.service.chrome_driver import ChromeDriver


def create_app():
    driver = ChromeDriver().get_driver()
    
    return driver