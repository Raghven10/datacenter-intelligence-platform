
from fastapi import FastAPI, Request, status
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.security import SECRET_KEY
from app.routes import auth, dashboard, equipment, equipment_types, inspection, places, roles, users, audit, notifications
from app.routes import pages, profile
import traceback

app = FastAPI(title="Datacenter DI System")

templates = Jinja2Templates(directory="app/templates")

# Add Session Middleware
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Custom Exception Handler for Flash Messages
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Check if the request is from a browser (accepts HTML)
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        request.session["flash_error"] = str(exc.detail)
        # Redirect back to the same page (referer) or home
        referer = request.headers.get("referer")
        if referer:
             return RedirectResponse(url=referer, status_code=status.HTTP_302_FOUND)
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    # For API/JSON requests, return standard JSON error
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Print stack trace to console
    traceback.print_exc()

    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return templates.TemplateResponse(
            "error.html", 
            {
                "request": request,
                "error_detail": str(exc),
                "user": None
            },
            status_code=500
        )
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(equipment.router)
app.include_router(equipment_types.router)
app.include_router(inspection.router)
app.include_router(pages.router)
app.include_router(places.router)
app.include_router(profile.router)
app.include_router(roles.router)
app.include_router(users.router)
app.include_router(audit.router)
app.include_router(notifications.router)
