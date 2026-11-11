from fastapi.templating import Jinja2Templates

# Single shared Jinja2Templates instance. Both main.py and the route modules
# import this so the templates directory string is defined in exactly one place.
templates = Jinja2Templates(directory="templates")
