# Full stack chat messaging app
Simple chat messaging app. User can create, login to accounts, view chats, send messages, view old messages, like messages, unlike messages and logout. Uses react and typescript in the frontend and Flask and Python in the backend. 
## Configuration for running Docker locally
```
# Make docker network
docker network create net

# Start mongodb container
docker run --name=mongo-example -d -p 27017:27017 --network net mongo:latest

# Build docker image if not built already:
docker build -t server . -f Dockerfile.server

# Start server container
docker run --rm -it -p 8080:5000 --network net server

# Start client locally in another terminal
cd client
npm start
```

## Notes about my implementation
All messages start with 0 votes, if a user wants to upvote it, the count increases by 1 and they can take back this vote to reduce the count by 1. The total count can't go below 0. Based on this, every message is implicitly downvoted already.

To prevent race conditions when liking or unliking a message, I use a lock.

User is authenticated in the backend using a token system. There is a known bug where the user is incorrectly unauthorized when they send too many requests to the backend at once. For regular use with this application, this bug isn't critical.