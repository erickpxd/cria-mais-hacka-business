import { ReactNode } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAppStore } from './store/AppStore'
import { ApprovalsPage, ArtworkPage, HomePage, LoginPage, NewProjectPage, ProjectDetailPage, ProjectsPage, ReviewPage } from './pages/Pages'
import './App.css'

function Protected({ children }: { children: ReactNode }) {
  const { session } = useAppStore()
  const location = useLocation()
  return session ? children : <Navigate to="/login" replace state={{ from: location.pathname }}/>
}

export default function App() {
  return <Routes>
    <Route path="/login" element={<LoginPage/>}/>
    <Route path="/" element={<Protected><HomePage/></Protected>}/>
    <Route path="/projetos" element={<Protected><ProjectsPage/></Protected>}/>
    <Route path="/projetos/novo" element={<Protected><NewProjectPage/></Protected>}/>
    <Route path="/projetos/:id" element={<Protected><ProjectDetailPage/></Protected>}/>
    <Route path="/artes/:id" element={<Protected><ArtworkPage/></Protected>}/>
    <Route path="/aprovacoes" element={<Protected><ApprovalsPage/></Protected>}/>
    <Route path="/aprovacoes/:id" element={<Protected><ReviewPage/></Protected>}/>
    <Route path="*" element={<Navigate to="/" replace/>}/>
  </Routes>
}
