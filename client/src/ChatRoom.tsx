import { Grid, TextField, Typography, ListItem, Button, Stack, Box, IconButton } from "@mui/material";
import { useState, useRef, useEffect } from "react";
import { useCookies } from 'react-cookie'
import { useParams } from 'react-router-dom';
import {socket} from './socket';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

function ChatRoom() {
    // Chat room component. Handles sending, receiving and displaying messages and liking, unliking and displaying likes
    let { uid } = useParams<string>()
    const [cookies, setCookie, removeCookie] = useCookies(['user'])
    const scrollRef = useRef<HTMLInputElement>(null);
    const [messages, setMessages] = useState([""]);
    const [currentMessage, setCurrentMessage] = useState("");
    const [scrollToBottom, setScrollToBottom] = useState(false);
    const [hoverInd, setHoverInd] = useState(-1)
    
    let users = [cookies.user, uid]
    users.sort()
    const user1 = users[0]
    const user2 = users[1]


    useEffect(() => {
        socket.on(user1 + user2, (e : any) => {
            setScrollToBottom(true)
            loadMessages()
        })

        socket.emit("refresh", "refresh")

        return () => {
            socket.off('refresh')
        }
    }, [])

    useEffect(() => {
        if (scrollRef.current && scrollToBottom) {
            scrollRef.current.scrollTo(0, scrollRef.current.scrollHeight)
            setScrollToBottom(false);
        }
        return;
    }, [scrollRef?.current?.scrollHeight])

    useEffect(() => {
        loadMessages();
        return;
    }, [])


    function handleLike(message_id : string){
        fetch("http://127.0.0.1:8080/update-like", {
            method: "POST",
            body: JSON.stringify({
                message_id: message_id,
                username: cookies.user,
                username2: uid
            }),
            headers: {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'},
            credentials: 'include'
        }).then((res) => {
            if (res.status == 401) {
                removeCookie("user", { path: "/"})
                window.location.replace("/")
                return;
            }
        }).catch((err) => {
            console.log(err)
        });
    }

    function loadMessages() {
        fetch("http://127.0.0.1:8080/get-messages", {
            method: "POST",
            body: JSON.stringify({
                sender: cookies.user,
                recipient: uid
            }),
            credentials: 'include',
            headers: {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        }).then(async (res) => {
            if (res.status == 200) {
                let data = await res.json()
                setMessages(data.value)
            }
            else if (res.status == 401) {
                removeCookie("user", { path: "/"})
                window.location.replace("/")
                return;
            }
            else {
                console.log(res.status)
            }
        });
        return [""]
    }

    function renderUpvoteButton(alreadyVoted : boolean, totalVotes : number, index : number, message_id : string, onLeft : boolean) { 
        return <Button size="small" 
            sx={{ borderRadius: "8px", minWidth: "8px", maxWidth: "8px", position: "relative", top: 15, left: (onLeft ? -5: "95%")}} 
            onClick={() => {handleLike(message_id)}} onMouseLeave={() => {setHoverInd(-1)}} onMouseOver={() => {setHoverInd(index)}} 
            variant="contained">{index == hoverInd ? (alreadyVoted ? -1 : "+1") : totalVotes}</Button>
    }

    function renderMessages() {
        return messages.map((message, i) => {
            if (message.length < 5) return;
            let msg = message[0]
            let timestamp = message[1]
            let upvotes = message[2]
            let sender = parseInt(message[3])
            let message_id = message[4]

            let upvoted = false;
            for (let ind = 0; ind < upvotes.length; ind++) {
                if (upvotes[ind] === cookies.user) {
                    upvoted = true;
                }
            }
            let ourSide = user1 === cookies.user ? 1 : 2
            return <ListItem key={i} style={{width: "100%" }} >
                <Grid container direction="row" alignItems="flex-end" justifyContent={sender != ourSide ? "flex-start" : "flex-end"} sx={{minWidth: "fit-content", minHeight: "fit-content", borderRadius: 1 }}>
                    {sender == ourSide ? 
                    <>
                        <Grid item xs={2} >
                            {renderUpvoteButton(upvoted, upvotes.length, i, message_id, sender != ourSide)}
                        </Grid>
                        <Grid item xs={10} style={{ border: "1px solid lightgrey", borderRadius: "10px", maxWidth: "fit-content", padding: "10px"}}>
                            <Typography >{msg}</Typography>
                        </Grid>
                    </>
                    :
                    <>
                        <Grid item xs={10} style={{ border: "1px solid lightgrey", borderRadius: "10px", maxWidth: "fit-content", padding: "10px"}}>
                            <Typography >{msg}</Typography>
                        </Grid>
                        <Grid item xs={2} >
                            {renderUpvoteButton(upvoted, upvotes.length, i, message_id, sender != ourSide)}
                        </Grid>
                    </>
                    }
                </Grid>
            </ListItem>
        });
    }

    async function handleSendMessage(e : any) {
        if (currentMessage.length == 0) return;
        fetch("http://127.0.0.1:8080/send-message", {
            method: "POST",
            body: JSON.stringify({
                sender: cookies.user,
                recipient: uid,
                message: currentMessage
            }),
            headers: {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'},
            credentials: "include"
        }).then((res) => {
            console.log(res.status)
            if (res.status == 401) {
                removeCookie("user", { path: "/"})
                window.location.replace("/")
                return;
            }
        })
    }

    return (
        <Grid container columnSpacing="20" style={{maxHeight: "100vh", overflow:"auto"}}>
            <Grid item xs = {2} >
                <IconButton onClick={() => {window.location.replace("/")}}><ArrowBackIcon/></IconButton>
            </Grid>
            <Grid item xs = {8} alignContent="center">
                <Typography textAlign="center" fontSize={30}>{uid}</Typography>
            </Grid>
            <Grid item xs={12} >
                <Stack ref={scrollRef} direction="column" style={{overflow: 'auto', height: "80vh", width: "100%"}}>
                    {renderMessages()}
                </Stack>
            </Grid>
            <Grid item xs = {11} >
                <TextField label="Enter Message" onChange={(e) => setCurrentMessage(e.target.value)} style={{width: "100%"}}></TextField>
            </Grid>
            <Grid item xs = {1}>
                <Button variant="contained" onClick={handleSendMessage}>Send</Button>
            </Grid>
        </Grid>
    )
}

export default ChatRoom;