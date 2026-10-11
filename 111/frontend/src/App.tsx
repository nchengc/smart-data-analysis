import { Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Workspace from './pages/Workspace'

const AUTH_KEY = 'sda_authed'

function isAuthed(): boolean {
  return localStorage.getItem(AUTH_KEY) === '1'
}

function RequireAuth({ children }: { children: JSX.Element }) {
  if (!isAuthed()) {
    return <Navigate to="/login" replace />
  }
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/workspace"
        element={
          <RequireAuth>
            <Workspace />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to={isAuthed() ? '/workspace' : '/login'} replace />} />
    </Routes>
  )
}

export { AUTH_KEY }
