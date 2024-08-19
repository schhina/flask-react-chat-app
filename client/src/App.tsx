import Login from './Login';
import ChatRoom from './ChatRoom';
import Home from './Home';
import { useCookies } from 'react-cookie'
import { createBrowserRouter, RouterProvider, useParams, useMatch } from 'react-router-dom';


function App() {
  const [cookies, setCookie] = useCookies(['user'])

  const router = createBrowserRouter([
    {
      path: '/',
      element: reroute()
    },
    {
      path: '/home',
      element: <Home />
    },
    {
      path: '/chat/:uid',
      element: <ChatRoom />
    }
  ])

  function reroute() {
    if (cookies.user) {
      return <Home />
    }
    return <Login onLogin={handleLogin} />
  }

  function handleLogin(user : string) {
    setCookie('user', user, { path: '/' })
    window.location.replace("/home")
  }

  return <RouterProvider router={router} />
}

export default App;
