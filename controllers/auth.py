from flask import Blueprint, request, jsonify
from db.prisma import db  
import bcrypt
from utils import setCookie
import httpx

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/register', methods=['POST'])
async def create_user():
    await db.connect()
    print(db.is_connected(), "is db conected")
    data = request.get_json()
    
    # Validate input
    if 'email' not in data or 'name' not in data or 'password' not in data:
        return jsonify({'error': 'Email, name, and password are required'}), 400
    
    email = data['email']
    name = data['name']
    password = data['password']
    
    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    try:
        # Create a new user with async Prisma
        user = await db.user.create(
            data={
                'email': email,
                'name': name,
                'password': hashed_password.decode('utf-8'),  # Store the hashed password as a string
            }
        )

        # Call setCookie to generate the response
        response = await setCookie(user)
        return response
    
    except Exception as e:
        print(e, "here is erorr")  # Output the error to the console for debugging
        return jsonify({'error': str(e)}), 500
    finally: 
        await db.disconnect()

@auth_blueprint.route('/google', methods=['POST'])
async def google_auth():
    await db.connect()
    
    data = request.get_json()

    access_token = data.get('access_token')
    if not access_token:
        return jsonify({"error": "No access token provided"}), 400

    async with httpx.AsyncClient() as client:
        token_info_response = await client.get(f'https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={access_token}')
        user_info_response = await client.get(f'https://www.googleapis.com/oauth2/v1/userinfo?access_token={access_token}')

    token_info = token_info_response.json()
    user_data = user_info_response.json()

    if not token_info or not user_data:
        return jsonify({"error": "Invalid token"}), 400

    email = user_data.get('email')
    name = user_data.get('name')
    
    try:
        user = await db.user.find_unique(where={"email": email})
        is_new_user = False
        
        if not user:
            # Create a new user with async Prisma
            user = await db.user.create(
                data={
                    'email': email,
                    'name': name,
                }
            )
            is_new_user = True

        # Call setCookie to generate the response
        response = await setCookie(user)
        
        # Add newUser flag to the response
        response_data = response.get_json()
        response_data['newUser'] = is_new_user
        return jsonify(response_data), response.status_code
    
    except Exception as e:
        print(e, "here is error")  # Output the error to the console for debugging
        return jsonify({'error': str(e)}), 500
    finally: 
        await db.disconnect()

# Add the login route
@auth_blueprint.route('/login', methods=['POST'])
async def login_user():
    await db.connect()
    print(db.is_connected(), "is db conected")
    data = request.get_json()

    # Validate input
    if 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Email and password are required'}), 400

    email = data['email']
    password = data['password']

    try:
        # Find the user by email
        user = await db.user.find_unique(where={"email": email})
        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401

        # Check if the password matches
        if not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            return jsonify({'error': 'Invalid email or password'}), 401

        # Call setCookie to generate the response
        response = await setCookie(user)
        return response

    except Exception as e:
        print(e, "here is error")  # Output the error to the console for debugging
        return jsonify({'error': str(e)}), 500
    finally:
        await db.disconnect()