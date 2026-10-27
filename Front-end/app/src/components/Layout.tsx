import { ReactNode, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import productImage from '../assets/figma/product.png'
import criaMaisLogo from '../assets/cria-mais-logo.png'
import { statusLabels, type ArtworkStatus, type Briefing } from '../domain/types'
import { useAppStore } from '../store/AppStore'

export function Button({ children, variant = 'primary', onClick, type = 'button', disabled }: { children: ReactNode; variant?: 'primary'|'secondary'|'danger'|'ghost'; onClick?: () => void; type?: 'button'|'submit'; disabled?: boolean }) {
  return <button type={type} className={`button ${variant}`} onClick={onClick} disabled={disabled}>{children}</button>
}

export function StatusPill({ status }: { status: ArtworkStatus }) {
  return <span className={`status ${status}`}>• {statusLabels[status]}</span>
}

export function PageTitle({ title, subtitle, action, eyebrow }: { title: string; subtitle?: string; action?: ReactNode; eyebrow?: string }) {
  return <div className="page-title"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>{action}</div>
}

function SidebarIcon({ name }: { name: 'home' | 'projects' | 'approvals' | 'chevron' | 'help' }) {
  const paths = {
    home: <><path d="m3 10.8 9-7.2 9 7.2"/><path d="M5.5 9.5V20h13V9.5"/><path d="M9.5 20v-6h5v6"/></>,
    projects: <><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M8 4V2.8M16 4V2.8M3 9h18"/></>,
    approvals: <><path d="M9 11.5 11.5 14 16 9.5"/><path d="M12 3 4.5 6v5.4c0 4.4 3.2 7.6 7.5 9.6 4.3-2 7.5-5.2 7.5-9.6V6L12 3Z"/></>,
    chevron: <path d="m8 10 4 4 4-4"/>,
    help: <><circle cx="12" cy="12" r="9"/><path d="M9.7 9a2.4 2.4 0 0 1 4.6 1c0 1.8-2.3 2.1-2.3 3.7M12 17.4v.1"/></>,
  }
  return <svg className={`sidebar-icon sidebar-icon-${name}`} viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>
}

export function CampaignPreview({ briefing, imageUrl, compact = false }: { briefing: Briefing; imageUrl?: string; compact?: boolean }) {
  return <div className={`campaign-art ${compact ? 'compact' : ''}`}>
    <div className="campaign-band">{briefing.channels[0]?.toUpperCase() || 'CAMPANHA'}</div>
    {imageUrl ? <img className="uploaded-preview" src={imageUrl} alt="Prévia da arte enviada"/> : <><div className="art-title">Promoção</div><b>{briefing.product}</b><small>Conteúdo demonstrativo</small><div className="price"><small>R$</small><strong>{briefing.price.replace('R$ ', '') || '—'}</strong></div><img src={productImage} alt="Embalagem demonstrativa de shampoo"/><div className="legal">{briefing.requiredText}</div></>}
  </div>
}

export function Shell({ children }: { children: ReactNode }) {
  const { session, switchRole, logout, data, loading, error, refresh } = useAppStore()
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  if (!session) return null
  const pending = data.artworks.filter(a => a.status === 'aguardando_aprovacao').length
  const leave = () => { logout(); navigate('/login') }
  return <div className="shell"><aside className="sidebar"><div className="brand"><img src={criaMaisLogo} alt="CriaMais — Mais tempo. Mais resultado." /></div><nav aria-label="Navegação principal"><NavLink to="/"><SidebarIcon name="home"/><span>Início</span></NavLink><NavLink to="/projetos"><SidebarIcon name="projects"/><span>Projetos</span></NavLink><NavLink to="/aprovacoes"><SidebarIcon name="approvals"/><span>Aprovações</span>{pending > 0 && <small className="count" aria-label={`${pending} aprovações pendentes`}>{pending}</small>}</NavLink></nav><div className="sidebar-bottom"><div className="demo-note"><b>Ambiente demonstrativo</b><span>Login fictício; dados persistidos e conferência por OCR/regras locais.</span></div><button className="profile" onClick={() => setOpen(v => !v)} aria-expanded={open} aria-haspopup="menu"><span className="avatar">{session.role === 'creator' ? 'AC' : 'RM'}</span><span><b>{session.name}</b><small>{session.role === 'creator' ? 'Criador' : 'Revisor humano'}</small></span><SidebarIcon name="chevron"/></button>{open && <div className="profile-menu" role="menu"><button role="menuitem" onClick={() => { switchRole(); setOpen(false); navigate(session.role === 'creator' ? '/aprovacoes' : '/') }}>Trocar para {session.role === 'creator' ? 'Revisor' : 'Criador'}</button><button role="menuitem" onClick={leave}>Sair</button></div>}</div></aside><section className="workspace"><header><div><b>Marketing</b><span>/</span><span>Produção criativa</span></div><div><span>POC local</span><button className="help-button" type="button" aria-label="Ajuda"><SidebarIcon name="help"/></button></div></header><main>{error && <div className="error-banner">{error} <button onClick={()=>void refresh()}>Tentar novamente</button></div>}{loading && <div className="loading-banner">Carregando dados do backend…</div>}{children}</main></section></div>
}
