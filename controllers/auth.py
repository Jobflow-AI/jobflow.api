from fastapi import APIRouter, Depends, HTTPException, Response, Body
from pydantic import BaseModel, EmailStr
from db.prisma import db
import bcrypt
import httpx
import jwt
import os
from datetime import datetime, timedelta
from typing import Optional

# Models
class UserRegister(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GoogleAuth(BaseModel):
    access_token: str

class TokenResponse(BaseModel):
    token: str
    user: dict
    newUser: Optional[bool] = False

# Router
auth_router = APIRouter()

DEFAULT_STATUSES = ["BOOKMARKED", "APPLIED", "ACCEPTED", "REJECTED"]
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key')

# Helper function to set JWT token
async def create_token(user):
    payload = {
        'id': user.id,
        'email': user.email,
        'exp': datetime.utcnow() + timedelta(days=30)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    
    # Convert user to dict for response
    user_dict = user.model_dump()
    
    return {"token": token, "user": user_dict}

@auth_router.post('/register', response_model=TokenResponse)
async def create_user(user_data: UserRegister):
    # Validate if user already exists
    existing_user = await db.user.find_unique(where={"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=409, detail="User with this email already exists")
    
    # Hash the password
    hashed_password = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt())
    
try:
# Create a new user
user = await db.user.create(
data={
'email': user_data.email,
'name': user_data.name,
'password': hashed_password.decode('utf-8'),
}
)
except Exception as e:
print(f"Error creating user: {e}")
raise HTTPException(status_code=500, detail="Failed to create user")

        # Create default job statuses
        for status in DEFAULT_STATUSES:
            await db.job_statuses.create(data={
                "user": {"connect": {"id": user.id}},
                "label": status,
                "value": 0
            })

        # Generate token response
        token_response = await create_token(user)
        return token_response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth_router.post('/google', response_model=TokenResponse)
async def google_auth(auth_data: GoogleAuth):
    access_token = auth_data.access_token
    
    async with httpx.AsyncClient() as client:
        token_info_response = await client.get(f'https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={access_token}')
        user_info_response = await client.get(f'https://www.googleapis.com/oauth2/v1/userinfo?access_token={access_token}')

    token_info = token_info_response.json()
    user_data = user_info_response.json()

    if not token_info or not user_data:
        raise HTTPException(status_code=400, detail="Invalid token")

    email = user_data.get('email')
    name = user_data.get('name')
    
    try:
        user = await db.user.find_unique(where={"email": email})
        is_new_user = False
        
        if not user:
            user = await db.user.create(data={'email': email, 'name': name})
            is_new_user = True

            # Create default job statuses for new Google user
            for status in DEFAULT_STATUSES:
                await db.job_statuses.create(data={
                    "user": {"connect": {"id": user.id}},
                    "label": status,
                    "value": 0
                })

        # Generate token response
        token_response = await create_token(user)
        token_response["newUser"] = is_new_user
        return token_response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth_router.post('/login', response_model=TokenResponse)
async def login_user(login_data: UserLogin):
    # Validate input
    if not login_data.email or not login_data.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    try:
        # Find the user by email
        user = await db.user.find_unique(where={"email": login_data.email})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Check if the password matches
        if not bcrypt.checkpw(login_data.password.encode('utf-8'), user.password.encode('utf-8')):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Generate token response
        token_response = await create_token(user)
        return token_response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))