from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os
from db.prisma import db

security = HTTPBearer()
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key')

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        print(token)
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        user_id = payload.get('id')
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        
        user = await db.user.find_unique(where={"id": user_id})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Optional function for routes that don't require authentication
async def get_optional_user(request: Request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        user_id = payload.get('id')
        
        if not user_id:
            return None
        
        user = await db.user.find_unique(where={"id": user_id})
        return user
    except:
        return None