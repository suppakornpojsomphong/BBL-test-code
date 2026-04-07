from fastapi import FastAPI, Request, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import jwt
from datetime import datetime, timedelta

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SECRET_KEY = "bbl_assessment_secret_key"
ALGORITHM = "HS256"

# In-memory Data Store 
# User Model: username, password, is_admin
users_db = {
    "admin-note": {"username": "admin-note", "password": "123", "is_admin": True},
    "user-1": {"username": "user-1", "password": "456", "is_admin": False}
}

bookings = []


def create_access_token(data: dict):
    to_encode = data.copy()
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(request: Request):
    token = request.cookies.get("session_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        return users_db.get(username)
    except Exception:
        return None

# --- Routes ---

# [GET] Login page
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    if get_current_user(request):
        return RedirectResponse(url="/booking")
    
    # In case: ERROR
    return templates.TemplateResponse(
        request, 
        "login.html", 
        {"request": request, "error": error}
    )

# [POST] Login page
@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    user = users_db.get(username)
    
    if not user or user["password"] != password:
        return RedirectResponse(url="/?error=1", status_code=status.HTTP_303_SEE_OTHER)
    
    token = create_access_token({"sub": username})
    response = RedirectResponse(url="/booking", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="session_token", value=token, httponly=True)
    return response

# [GET] Booking page - Entering page
@app.get("/booking", response_class=HTMLResponse)
async def booking_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    # Admin can sees everything.
    if user["is_admin"]:
        display_bookings = bookings

        
    # Users can see only their own bookings.
    else:
        display_bookings = [b for b in bookings if b["user"] == user["username"]]

    return templates.TemplateResponse(
        request, 
        "booking.html", 
        {
            "request": request, 
            "user": user, 
            "bookings": display_bookings
        }
    )

# [GET] Booking page - Create Booking
@app.post("/book")
async def create_booking(
    request: Request, 
    start_time: str = Form(...), 
    end_time: str = Form(...)
):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)
    
    # Server-side time validation
    if start_time >= end_time:
        return RedirectResponse(url="/booking?error=time", status_code=303)

    slot_string = f"{start_time} - {end_time}"
    
    bookings.append({
        "user": user["username"],
        "slot": slot_string
    })
    
    return RedirectResponse(url="/booking", status_code=303)

# [GET] Logout
@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("session_token")
    return response

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="127.0.0.1", port=8000)