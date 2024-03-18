import os
from dotenv import load_dotenv
from exceptions import MessageBoxException

load_dotenv(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".env"))

api_token = os.getenv("TOKEN")
address = os.getenv("ADDRESS")
data_dir = os.getenv("DATA_DIR")
api_url = os.getenv("API_URL")

if api_token in [None, ""]: raise MessageBoxException("Specify TOKEN in .env file")
if address in [None, ""]: raise MessageBoxException("Specify ADDRESS in .env file")
if api_token in [None, ""]: raise MessageBoxException("Specify DATA_DIR in .env file")
if api_url in [None, ""]: raise MessageBoxException("Specify API_URL in .env file")


templates_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates")

class ColorBGR:
    red = (0, 0, 255)
    lime = (0, 255, 0)
    blue = (255, 0, 0)
    lightBlue = (170, 178, 32)
    yellow = (0, 255, 255)
    cyan = (255, 255, 0)
    magenta = (255, 0, 255)
    orange = (0, 140, 255)
    olive = (35, 142, 107)
    green = (0, 128, 0)
    purple = (211, 0, 148)
    pink = (180, 20, 255)
    black = (0, 0, 0)
    white = (255, 255, 255)
    gray = (192, 192, 192)
    brown = (19, 69, 139)
    color1 = (1, 1, 1)






