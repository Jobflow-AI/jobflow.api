import os
from fastapi import Response
from fastapi.responses import JSONResponse
import jwt

JWT_SECRET_TOKEN = os.getenv('JWT_SECRET')

async def setCookie(user, response: Response):
    payload = {
        'id': user.id,
    }
    token = jwt.encode(payload, JWT_SECRET_TOKEN, algorithm='HS256')

    # Serialize the user object to a dictionary
    user_data = user.model_dump()

    # Set the cookie
    response.set_cookie(
        'token',
        value=token,
        httponly=True,
        secure=True,  # Use HTTPS in production
        samesite='none',  # Ensure cookies work in cross-site contexts
        max_age=7 * 24 * 60 * 60,  # 7 days in seconds
        domain=".jobflow.in"
    )

    # Return response data
    return {"success": True, "message": "User created successfully", "token": token, "user": user_data}


