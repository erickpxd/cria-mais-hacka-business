export type Role = 'creator' | 'reviewer'
export type ArtworkStatus = 'em_analise' | 'em_producao' | 'precisa_de_ajustes' | 'aguardando_aprovacao' | 'aprovada'

export interface DemoSession {
  name: string
  role: Role
}

export interface Briefing {
  objective: string
  description: string
  deadline?: string
  product: string
  price: string
  requiredText: string
  channels: string[]
  source: 'manual' | 'document_pending_transcription'
  sourceFileName?: string
  sourceToken?: string
}

export interface BriefingExtraction {
  token: string
  campaignName?: string
  product?: string
  price?: string
  objective?: string
  deadline?: string
  requiredText?: string
  channels: string[]
  warnings: string[]
}

export interface HistoryEntry {
  id: string
  at: string
  actor: string
  role: Role
  action: string
  comment?: string
}

export interface Artwork {
  id: string
  projectId: string
  name: string
  channel: string
  fileName: string
  previewDataUrl?: string
  status: ArtworkStatus
  comments: string[]
  history: HistoryEntry[]
  analysis?: {
    state: 'queued' | 'processing' | 'completed' | 'failed' | 'concluida' | 'erro'
    error?: string
    notes: string[]
    findings: Array<{
      id: number
      order: number
      type: 'preco_divergente' | 'erro_escrita' | 'texto_na_borda' | string
      title: string
      description: string
      reference?: string
      observed?: string
      expected?: string
      confidence?: number
      region?: { nx: number; ny: number; nw: number; nh: number }
    }>
  }
  templateData?: TemplateData
}

export interface TemplateData {
  product: string
  price: string
  objective: string
  requiredText: string
}

export interface Project {
  id: string
  name: string
  createdAt: string
  briefing: Briefing
  artworkIds: string[]
}

export interface AppData {
  projects: Project[]
  artworks: Artwork[]
}

export const statusLabels: Record<ArtworkStatus, string> = {
  em_analise: 'Em análise',
  em_producao: 'Em produção',
  precisa_de_ajustes: 'Precisa de ajustes',
  aguardando_aprovacao: 'Aguardando aprovação',
  aprovada: 'Aprovada',
}
