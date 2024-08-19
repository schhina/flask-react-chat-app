import { useState } from 'react';
import { Grid, Typography, TextField, Button, CircularProgress, Stack } from '@mui/material';

const centerStyle = {display: "flex", justifyContent: "center", alignContent: "center"}

function Login({ onLogin }: { onLogin : Function }) {
    // Login/createaccount component. Handles validating input and sending login and create account requests.
    const [ username, setUsername ] = useState("")
    const [ password, setPassword ] = useState("")
    const [ secondPass, setSndPass] = useState("")
    const [ showCreateAccount, setShowCreateAccount ] = useState(false)
    const [ errMsg, setErrMsg ] = useState("")
    const [ showLoadingBubble, setShowLoadingBubble ] = useState(false)

    function handleLoginClick(e : any) {
        setShowLoadingBubble(true);
        setErrMsg("")
        fetch("http://127.0.0.1:8080/login", {
            method: "POST",
            body: JSON.stringify({
                username: username,
                password: password
            }),
            headers: {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'},
            credentials: 'include'
        }).then((res) => {
            console.log(res.status)

            if (res.status == 400){
                setErrMsg("Bad request")
            }
            else if (res.status == 401){
                setErrMsg("Wrong password")
            }
            else if (res.status == 404) {
                setErrMsg("User not found")
            }
            else{
                onLogin(username)
            }
        }).finally(() => {
            setShowLoadingBubble(false)
        });
    }

    function handleCreateAccountClick(e : any) {
        setErrMsg("")
        // Validate username and password

        if (username.length === 0) {
            setErrMsg("Invalid username")
            return;
        }
        if (password != secondPass) {
            setErrMsg("Passwords don't match")
            return;
        }
        if (password.length < 4) {
            setErrMsg("Password must be at least 4 characters long")
            return;
        }
        // Maybe verify password contains a special character
        if (showLoadingBubble) {
            return;
        }
        setShowLoadingBubble(true);

        fetch("http://127.0.0.1:8080/create-account", {
            method: "POST",
            body: JSON.stringify({
                username: username,
                password: password
            }),
            credentials: 'include',
            headers: {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        }).then(async (res) => {
            let data = await res.json()
            console.log(res.status)
            if (res.status != 200) {
                console.log("error")
                setErrMsg(data.error)
            }
            else {
                console.log("Account Created")
                onLogin(username)
            }
        }).finally(() => {
            setShowLoadingBubble(false)
        });
    }

    function switchRender(e : any) {
        setErrMsg("")
        setShowCreateAccount(!showCreateAccount)
    }

    function renderError(){
        return <Grid item xs={12}>
            <Typography color="red">{errMsg}</Typography>
            </Grid>
    }

    function renderBubble(msg : string, callBack : any) {
        if (showLoadingBubble)
            return (
                <Grid item xs={12} sx={centerStyle} direction="row" alignItems="center">
                    <Grid item xs={12} sx={centerStyle}>
                        <CircularProgress />
                    </Grid>
                </Grid>
            )
        return (
                <Grid item xs={12} sx={centerStyle} direction="row" alignItems="center">
                    <Grid item xs={12} sx={centerStyle}>
                        <Button variant="contained" onClick={callBack}>{msg}</Button>
                    </Grid>
                </Grid>
        )
    }
    
    function renderSwitchButton(msg : string) {
        return <Grid item xs={12}>
            <Button size="small" variant="text" id="createAccount" onClick={switchRender}>    
                {msg}
            </Button>
        </Grid>
    }

    function renderTextFields(title : string) {
        return <>
        <Grid item xs={12}>
            <Typography fontSize={40}>
                {title} 
            </Typography>
        </Grid>
        <Grid item xs={12} sx={{ width: "100%" }}>
            <TextField sx={{ width: "100%" }} id="username" label="Username" variant="standard" onChange={(e : any) => setUsername(e.target.value)} />
        </Grid>
        <Grid item xs={12} sx={{ width: "100%" }}>
            <TextField sx={{ width: "100%" }} id="password" label="Password" variant="standard" type="password" onChange={(e : any ) => setPassword(e.target.value)} />
        </Grid>
        <Grid item xs={12} sx={{ width: "100%" }}>
            <TextField sx={{ width: "100%", visibility: (title === "Login" ? "hidden" : "visible")}} 
            variant="standard" type="password" label="Verify Password" id="createAccountPasswordSnd" 
            onChange={(e) => setSndPass(e.target.value)}></TextField>
        </Grid>
        </>
    }

    function renderComponents(tfMsg : string, clickCallback : Function, switchText : string) {
        return <>
            <>{renderTextFields(tfMsg)}</>
            <>{errMsg.length != 0 ? renderError() : ""}</>
            <>{renderBubble(tfMsg, clickCallback)}</>
            <>{renderSwitchButton(switchText)}</>
        </>

    }

    return (<Grid container direction="column" alignItems="center" style={{ minHeight: '100vh', minWidth: "100vh"}}>
        <Grid container item xs={12} direction="column" alignItems="center" justifyContent="flex-start" spacing={3} style={{ minHeight: '100vh', width: "fit-content"}}>
            {showCreateAccount ? renderComponents("Create an account", handleCreateAccountClick, "Already have an account?") : renderComponents("Login", handleLoginClick, "Don't have an account?")}    
        </Grid>
    </Grid>)
        
}

export default Login;