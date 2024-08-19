import { useState, useEffect } from 'react';
import { Grid, Typography, TextField, Button, Stack, IconButton, Divider } from '@mui/material';
import { useCookies } from 'react-cookie'
import LogoutTwoToneIcon from '@mui/icons-material/LogoutTwoTone';

function Home() {
    // Home/dashboard for user component. Handles starting new chats and displaying existing chats.
    const [ cookies, setCookie, removeCookie ] = useCookies(['user'])
    const [ recipients, setRecipients ] = useState([])
    const [ username, setUsername ] = useState("")

    async function initRecipients() {
        if (cookies.user) {

            let data = await fetch("http://127.0.0.1:8080/get-chats/" + cookies.user, {
                method: "POST",
                credentials: 'include',
                headers: {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
            }).then(async (res) => {
                let data = await res.json()
                console.log(data)

                if (res.status === 400) {
                    console.log("username not sent correctly")
                }
                else if (res.status === 404) {
                    console.log("User not found")
                    removeCookie('user', { path: '/' })
                    window.location.replace("/")
                }
                else if (res.status == 401) {
                    removeCookie('user', { path: '/'})
                    window.location.replace("/")
                }
                else {
                    return data.value
                }
                return [""]
            })
            return setRecipients(data)
        }
        else {
            console.log("User not logged in")
            window.location.replace("/")
            return setRecipients([])
        }
    }


    useEffect(() => {
        initRecipients();
    }, [])


    function handleNewChat() {
        fetch("http://127.0.0.1:8080/new-chat", {
            method: "POST",
            body: JSON.stringify({
                current_user: cookies.user,
                new_user: username
            }),
            credentials: 'include',
            headers: {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        }).then((res) => {
            console.log(res.status)
            if (res.status === 200) {
                window.location.replace("/chat/" + username)
            }
            else if (res.status == 401) {
                removeCookie('user', { path: '/'})
                window.location.replace("/chat/" + username)
            }
            else {
                console.log("user not found")
            }
        });
    }

    function handleViewChat(e : any, id : string) {
        window.location.replace("/chat/" + id)
    }

    function handleLogout(e : any) {
        fetch("http://127.0.0.1:8080/logout", {
            method: "POST",
            body: JSON.stringify({
                username: cookies.user
            }),
            credentials: 'include',
            headers: {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        })
        removeCookie('user', { path: '/' })
        window.location.replace("/")
    }

    function renderChats() {
        return recipients.map((id : string, i : number) => {
                return <Button variant="text" onClick={(e) => handleViewChat(e, id)} sx={{ minWidth: "100%"}}>{id}</Button>
        })
    }

    return (recipients && (
    <Grid container columnSpacing="20" rowSpacing="10" justifyContent="space-around" style={{maxHeight: "100vh", overflow:"auto"}}>
        <Grid item xs={11}>
            <Typography fontSize={40}>Chats</Typography>
        </Grid>
        <Grid item xs={1} alignContent="flex-start" justifyContent="flex-end">
            <IconButton onClick={handleLogout} >
                <LogoutTwoToneIcon />
            </IconButton>
        </Grid>
        <Grid item xs={10}>
            <TextField onChange={(e) => setUsername(e.target.value)} sx={{ minWidth: "100%"}}></TextField>
        </Grid>
        <Grid item xs={2} onClick={handleNewChat}>
            <Button variant="outlined">Message new user</Button>
        </Grid>
        <Grid item xs={12}>
        </Grid>
        <Stack direction="column" justify-content="flex-start" alignContent="flex-start" style={
            {overflow: 'auto', height: "80vh", minWidth: "100%"}} divider={<Divider flexItem/>}>
            {renderChats()}
        </Stack>
    </Grid>))
}

export default Home