from flask import Flask, request, Response, make_response
import json
from pymongo import MongoClient
from bson.objectid import ObjectId
import time
from flask_socketio import SocketIO
import random

con_string = "mongodb://mongo-example:27017/serverSelectionTimeoutMS=2000"
client = MongoClient(con_string)
db = client.test_db
user_coll = db.users
chat_coll = db.chats
mess_coll = db.messages
token_coll = db.tokens

locked_votes = set()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins=["http://127.0.0.1:3000", "http://localhost:3000"])
    
def extract_tokens(cookies):
    """
    Given cookies, return the access token and refresh token. Returns empty string if a respective token isn't found.

    Parameters:
    - cookies: A request.cookies object

    Returns: (access_token, refresh_token)
    """
    return (cookies.get("access_token", ""), cookies.get("refresh_token", ""))
    
def generate_token():
    """
    Generates an access token, refresh token and their timeouts
    The tokens are a random sequence of 10 characters

    Returns: (access_token, access_token timeout, refresh_token, refresh_token timeout)
    """
    return ("".join([random.choice(chr(random.randint(ord('A'), ord('z')))) for i in range(10)]), time.time() + 60*15 , "".join([random.choice(chr(random.randint(ord('A'), ord('z')))) for i in range(10)]), time.time() + 60*120)

def add_auth_tokens(res, a_tok, r_tok):
    """
    Add cookies to the response object to set the access token and refresh token on the client

    Parameters:
    - res: Response object (Gets modified in function)
    - a_tok: String representing access token
    - r_tok: String representing refresh token

    Returns:
    - Response object with new headers.
    """
    res.set_cookie("access_token", a_tok, samesite="none", secure=True, httponly=True)
    res.set_cookie("refresh_token", r_tok, samesite="none", secure=True, httponly=True)
    return res

def _auth(user, acc_token, refresh_token):
    """
    Authorization helper function. Determines if given tokens are valid for a given user. If they're expired and can be refreshed, 
    refresh and return the new tokens. If user isn't authenticated we return empty strings as the new tokens. If everything is valid,
    we return the given tokens.

    Parameters:
    - user: String representing current user
    - acc_token: String representing access token
    - refresh_token: String representing refresh token

    Returns: (boolean, string, string)
    - boolean representing if the user is authorized
    - access token (will be different if we refresh or are unauthorized)
    - refresh token (will be different if we refresh or are unauthorized)
    """

    token_doc = token_coll.find_one({"username": user, "a_tok": acc_token, "r_tok": refresh_token})
    if not token_doc:
        print("Not found")
        return False, "", ""
    
    
    curr = time.time()
    if token_doc['a_tok_ttl'] >= curr: # Token isn't expired
        return True, acc_token, refresh_token
    elif token_doc['a_tok_ttl'] < curr and token_doc['r_tok_ttl'] >= curr: # Token expired but we can refresh
        q_remove = user_coll.update_one({"username": user}, {"$pull": {"tokens": str(token_doc["_id"])}})
        if q_remove.modified_count < 1:
            return False, "", ""

        token_coll.delete_one(token_doc)
        a_tok, a_tok_ttl, r_tok, r_tok_ttl = generate_token()
        token_id = token_coll.insert_one({
            "username": user, 
            "a_tok": a_tok, 
            "a_tok_ttl": a_tok_ttl,
            "r_tok": r_tok,
            "r_tok_ttl": r_tok_ttl}).inserted_id
        
        q_insert = user_coll.update_one({"username": user}, {"$push": {"tokens": str(token_id)}})
        if q_insert.modified_count < 1:
            return False, "", ""

        return True, a_tok, r_tok
    else: # Both tokens expired
        q_remove = user_coll.update_one({"username": user}, {"$pull": {"tokens": (str(token_doc["_id"]))}})
        if q_remove.modified_count < 1:
            return False, "", ""

        token_coll.delete_one(token_doc)
        return False, "", ""
    
def authenticate(cookies, user):
    """
    Function endpoints call to determine if user is authenticated. Returns tokens to set based on authorization

    Parameters:
    - cookies: request.cookies
    - user: String for user's username

    Returns: (boolean, string, string)
    - boolean representing if the user is authorized
    - access token (will be different if we refresh or are unauthorized)
    - refresh token (will be different if we refresh or are unauthorized)
    """
    a_tok, r_tok = extract_tokens(cookies)
    return _auth(user, a_tok, r_tok)

def logout(cookies, username):
    """
    Log user out by removing their cookies from db.

    Parameters:
    - cookies: request.cookies
    - username: user's username

    Returns:
    - True or false depending on if we deleted the cookies
    """
    a_tok, r_tok = extract_tokens(cookies)
    token_doc = token_coll.find_one({"username": username, "a_tok": a_tok, "r_tok": r_tok})
    if not token_doc:
        return False
    
    q_remove = user_coll.update_one({"username": username}, {"$pull": {"tokens": str(token_doc["_id"])}})
    token_coll.delete_one(token_doc)
    return True

# @app.route("/")
# def hello_world():
#     print("here")
#     return "<p>Hello, World!</p>"

@app.route("/logout", methods=["POST"])
def logout_route():
    """
    Endpoint to logout. POST method. Expecting tokens to be in cookies

    In body:
    - username: The user we are logging out
    """
    data = json.loads(request.get_data(as_text=True))

    if "username" not in data:
        return generate_response(400, json.dumps({"error": "Bad request"}), "", "")
    
    username = data['username']
    logout(request.cookies, username)
    return generate_response(200)

@app.route("/update-like", methods=["POST"])
def like_message():
    """
    Like or unlike a given message by a given user. If the user already liked it, we will unlike and vice versa. POST method. Expecting tokens to be in cookies.
    Emits an update that the chat has changed.

    In body:
    - username: The user that sent the request
    - message_id: The message {username} is modifiying
    - username2: The other user in the chat
    """
    data = json.loads(request.get_data(as_text=True))
    a_tok, r_tok = extract_tokens(request.cookies)
    if "username" not in data:
        return generate_response(400, json.dumps({"error": "Bad request"}), a_tok, r_tok)
    if "message_id" not in data:
        return generate_response(400, json.dumps({"error": "Bad request"}), a_tok, r_tok)
    if "username2" not in data:
        return generate_response(400, json.dumps({"error": "Bad request"}), a_tok, r_tok)
    
    username  = data['username']
    username2 = data['username2']
    m_id      = data['message_id']

    valid, a_tok, r_tok = authenticate(request.cookies, username)
    if not valid:
        return generate_response(401, json.dumps({"error": "Unauthorized"}), a_tok, r_tok)

    m_doc = mess_coll.find_one({"_id": ObjectId(str(m_id))})
    if not m_doc:
        return generate_response(400, json.dumps({"error": "Bad request"}), a_tok, r_tok)
    
    while m_id in locked_votes:
        time.sleep(0.1)
    
    locked_votes.add(m_id)

    if username in m_doc['upvotes']:
        query = mess_coll.update_one(
            {"_id": ObjectId(str(m_id))}, 
            {"$pull": {"upvotes": username}},
            )
    else:
        query = mess_coll.update_one({"_id": ObjectId(str(m_id))}, {"$push": {"upvotes": username}})

    locked_votes.remove(m_id)

    if query.modified_count < 1:
        return generate_response(500, json.dumps({"error": "Error updating"}), a_tok, r_tok)
    
    user1, user2 = sorted((username, username2))
    socketio.emit(f"{user1 + user2}", "like update")
    return generate_response(200, "", a_tok, r_tok)


@app.route("/get-messages", methods=["POST"])
def get_messages():
    """
    Return all messages of a given chat. POST method. Expecting tokens to be in cookies.

    In body:
    - sender: The user requesting the messages
    - recipient: The other user in the chat
    """
    a_tok, r_tok = extract_tokens(request.cookies)
    data = json.loads(request.get_data(as_text=True))
    if "sender" not in data:
        return generate_response(400, json.dumps({"error": "Bad request"}), a_tok, r_tok)
    if "recipient" not in data:
        return generate_response(400, json.dumps({"error": "Bad request"}), a_tok, r_tok)
    
    user1, user2 = sorted([str(data['sender']), str(data['recipient'])])

    valid, a_tok, r_tok = authenticate(request.cookies, data['sender'])
    if not valid:
        return generate_response(401, json.dumps({"error": "Unauthorized"}), a_tok, r_tok)

    chat_doc = chat_coll.find_one({"user1": user1, "user2": user2})
    if not chat_doc:
        return generate_response(400, json.dumps({"error": "Bad request"}), a_tok, r_tok)

    messages = chat_doc['messages']
    res = []
    for m_id in messages:
        m_doc = mess_coll.find_one({"_id": ObjectId(str(m_id))})
        if not m_doc:
            continue
        res.append(m_doc)
    
    return generate_response(200, json.dumps({"value": [[v['message'], v['timestamp'], v['upvotes'], v['sender'], str(v['_id'])] for v in res]}), a_tok, r_tok)


@app.route("/login", methods=["POST"])
def login():
    """
    Login endpoint. Generates and sets access and refresh tokens in client. POST method

    In body:
    - username
    - password
    """
    data = json.loads(request.get_data(as_text=True))

    if "username" not in data:
        return generate_response(400, json.dumps({"error": "Bad Request"}))
    if "password" not in data:
        return generate_response(400, json.dumps({"error": "Bad Request"}))
    
    user_doc = user_coll.find_one({"username": data['username']})
    if user_doc is None:
        return generate_response(404, json.dumps({"error": "User not found"}))
    if user_doc['password'] != data['password']:
        return generate_response(401, json.dumps({"error": "Unauthorized"}))

    a_tok, a_tok_ttl, r_tok, r_tok_ttl = generate_token()
    user = user_doc['username']

    token_id = token_coll.insert_one({
        "username": user, 
        "a_tok": a_tok, 
        "a_tok_ttl": a_tok_ttl,
        "r_tok": r_tok,
        "r_tok_ttl": r_tok_ttl}).inserted_id
    
    query = user_coll.update_one({"username": user}, {"$push": {"tokens": str(token_id)}})
    if query.modified_count < 1:
        return generate_response(400, json.dumps({"error": "Bad request"}))

    return generate_response(200, "", a_tok, r_tok)



@app.route("/get-chats/<username>", methods=["GET"])
def get_chats(username):
    """
    Return all chats a user has. GET method. Expecting tokens to be in cookies
    """
    valid, a_tok, r_tok = authenticate(request.cookies, username)
    if not valid:
        return generate_response(401, json.dumps({"error": "Unauthorized"}), a_tok, r_tok)
    query = user_coll.find_one({"username": username})
    if query is None:
        return generate_response(404, json.dumps({"error": f'Not found'}), a_tok, r_tok)
    
    recipients = query['chats']
    return generate_response(200, json.dumps({"value": recipients}), a_tok, r_tok)

@app.route("/new-chat", methods=["POST"])
def new_chat():
    """
    Create a new chat between current_user and new_user. POST method. Expecting tokens to be in cookies

    In body:
    - current_user: User creating the chat
    - new_user: Other user in the chat
    """
    a_tok, r_tok = extract_tokens(request.cookies)
    data = json.loads(request.get_data(as_text=True))

    if "current_user" not in data:
        return generate_response(400, json.dumps({"error": "Bad Request"}), a_tok, r_tok)
    if "new_user" not in data:
        return generate_response(400, json.dumps({"error": "Bad Request"}), a_tok, r_tok)
    current_user = str(data['current_user'])
    new_user = str(data['new_user'])

    valid, a_tok, r_tok = authenticate(request.cookies, current_user)
    if not valid:
        return generate_response(401, json.dumps({"error": "Unauthorized"}), a_tok, r_tok)

    # Check if other user exists
    rec_doc = user_coll.find_one({"username": new_user})
    if rec_doc is None:
        return generate_response(400, json.dumps({"error": "Bad Request"}), a_tok, r_tok)

    query = user_coll.update_one({"username": current_user}, {"$push": {"chats": new_user}})
    if query.modified_count < 1:
        return generate_response(404, json.dumps({"error": "User not found"}), a_tok, r_tok)
    
    return generate_response(200, "", a_tok, r_tok)


@app.route("/send-message", methods=["POST"])
def send_message():
    """
    Send a message in a given chat. POST method. Expecting tokens to be in cookies

    In body:
    - message: message to be sent
    - recipient: User receiving the message
    - sender: User sending the message
    """
    a_tok, r_tok = extract_tokens(request.cookies)

    data = json.loads(request.get_data(as_text=True))

    if "message" not in data:
        return generate_response(400, json.dumps({"error": "Bad Request"}), a_tok, r_tok)
    if "recipient" not in data:
        return generate_response(400, json.dumps({"error": "Bad Request"}), a_tok, r_tok)
    if "sender" not in data:
        return generate_response(400, json.dumps({"error": "Bad Request"}), a_tok, r_tok)
    

    msg = str(data['message'])
    sender = str(data['sender'])
    recipient = str(data['recipient'])
    user1, user2 = sorted([sender, recipient])

    valid, a_tok, r_tok = authenticate(request.cookies, sender)
    if not valid:
        return generate_response(401, json.dumps({"error": "Unauthorized"}), a_tok, r_tok)

    # Check if recipient exists
    rec_doc = user_coll.find_one({"username": recipient})
    if rec_doc is None:
        return generate_response(400, json.dumps({"error": "Bad Request, recipient doesn't exist"}), a_tok, r_tok)

    # Create message
    msg_doc = mess_coll.insert_one({"message": msg, "user1": user1, "user2": user2, "timestamp": time.time(), "upvotes": [], "sender": 1 if user1 == sender else 2})
    if not msg_doc.acknowledged:
        return generate_response(500, json.dumps({"error": "Couldn't create message"}), a_tok, r_tok)
    
    # Make chat document if it doesn't exist
    chat = chat_coll.find_one({"user1": user1, "user2": user2})
    if chat is None:
        chat_id = chat_coll.insert_one({"user1": user1, "user2": user2, "messages": []}).inserted_id
    else:
        chat_id = chat['_id']

    query = chat_coll.update_one({"user1": user1, "user2": user2}, {"$push": {"messages": f"{ObjectId(msg_doc.inserted_id)}"}})
    if query.modified_count < 1:
        return generate_response(500, json.dumps({"error": "Couldn't create message"}), a_tok, r_tok)

    # Make sure both parties know the chat is happening
    user_coll.update_one({"username": user1}, {"$addToSet": {"chats": user2}})
    user_coll.update_one({"username": user2}, {"$addToSet": {"chats": user1}})

    socketio.emit(f"{user1 + user2}", "new message")
    return generate_response(200, json.dumps({"value": "new message"}), a_tok, r_tok)

@app.route("/create-account", methods=["POST"])
def create_account():
    """
    Make a new account. POST method

    In body:
    - username: Username of new account
    - password: Password of new account
    """
    data = json.loads(request.get_data(as_text=True))

    if "username" not in data:
        return generate_response(401, json.dumps({"error": "Bad Request"}))
    elif "password" not in data:
        return generate_response(401, json.dumps({"error": "Bad Request"}))
    
    username = data['username']
    password = data['password']

    # Check if username already exists
    query = user_coll.find_one({"username": username})
    if query is not None:
        return generate_response(401, json.dumps({"error": "Username already exists"}))

    # TODO: Should do something to store password more securely
    try:
        a_tok, a_tok_ttl, r_tok, r_tok_ttl = generate_token()

        token_id = token_coll.insert_one({
            "username": username, 
            "a_tok": a_tok, 
            "a_tok_ttl": a_tok_ttl,
            "r_tok": r_tok,
            "r_tok_ttl": r_tok_ttl}).inserted_id

        user_coll.insert_one({
            "username": username,
            "password": password,
            "chats": [],
            "tokens": [str(token_id)] # token ids
        })
        return generate_response(200, "{}", a_tok, r_tok)
    except:
        pass
    
    return generate_response(500, json.dumps({"error": "Internal server error"}))

def generate_response(code, data = "", a_tok = "", r_tok = ""):
    """
    Helper method to create and add CORS and auth headers to response.

    Parameters:
    - code: status code
    - data: response body
    - a_tok: access token
    - r_tok: refresh token

    Returns:
    - response
    """
    res = make_response(data)
    res.status = code
    res.headers['Access-Control-Allow-Origin'] = "http://127.0.0.1:3000"
    res.headers['Access-Control-Allow-Credentials'] = "true"
    return add_auth_tokens(res, a_tok, r_tok)

# @socketio.on("refresh")
# def refresh(data):
#     print('refreshed')
#     socketio.emit("refresh", "hi")

if __name__ == "__main__":
    socketio.run(app, port=5000, debug=True)
    client.close()
    print("done")

# Username -> {password, list of chat refs indexed by other user}
# Chat -> {user1, user2, list of messages}
# Message -> {sender, receiver, content, list of people who've upvoted, timestamp}
# Token -> {user, access token, refresh token, access token ttl, refresh token ttl}

# Change message schema to not have user1 and user2


# --name=mongo-example mongo:latest
# docker run --rm -it -p 8080:5000 --network mong-net server
# docker run --name=mongo-example -d =p 27017:27017 --network mong-net mongo:latest