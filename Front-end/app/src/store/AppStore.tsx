import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import type {
  AppData,
  Artwork,
  Briefing,
  BriefingExtraction,
  DemoSession,
  Project,
  TemplateData,
} from "../domain/types";
import {
  approveArtworkApi,
  analyzeArtworkApi,
  createProjectApi,
  extractBriefingApi,
  generateTemplatesApi,
  loadData,
  returnArtworkApi,
  previewTemplateApi,
  saveTemplateApi,
  submitArtworkApi,
  uploadArtworkApi,
  uploadArtworkVersionApi,
} from "../services/api";

const SESSION_KEY = "cria-mais-poc-session-v2";
interface StoreValue {
  session: DemoSession | null;
  data: AppData;
  loading: boolean;
  error: string | null;
  login: () => void;
  logout: () => void;
  switchRole: () => void;
  refresh: () => Promise<void>;
  createProject: (name: string, briefing: Briefing) => Promise<string>;
  extractBriefing: (file: File) => Promise<BriefingExtraction>;
  addArtwork: (
    projectId: string,
    input: Pick<Artwork, "name" | "channel">,
    file: File,
  ) => Promise<void>;
  addArtworkVersion: (artworkId: string, file: File) => Promise<void>;
  generateTemplates: (projectId: string, channels: string[]) => Promise<void>;
  previewTemplate: (artworkId: string, data: TemplateData) => Promise<Blob>;
  saveTemplate: (artworkId: string, data: TemplateData) => Promise<void>;
  analyzeArtwork: (artworkId: string) => Promise<void>;
  submitArtwork: (id: string) => Promise<void>;
  approveArtwork: (id: string) => Promise<void>;
  returnArtwork: (id: string, comment: string) => Promise<void>;
  projectById: (id: string) => Project | undefined;
  artworkById: (id: string) => Artwork | undefined;
}
const Context = createContext<StoreValue | null>(null);
const readSession = (): DemoSession | null => {
  try {
    const v = localStorage.getItem(SESSION_KEY);
    return v ? JSON.parse(v) : null;
  } catch {
    return null;
  }
};

export function AppStoreProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<DemoSession | null>(readSession);
  const [data, setData] = useState<AppData>({ projects: [], artworks: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (session) localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    else localStorage.removeItem(SESSION_KEY);
  }, [session]);
  const refresh = useCallback(async () => {
    if (!session) return;
    setLoading(true);
    setError(null);
    try {
      setData(await loadData(session.role));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Backend indisponível.");
    } finally {
      setLoading(false);
    }
  }, [session]);
  useEffect(() => {
    void refresh();
  }, [refresh]);
  useEffect(() => {
    if (!session || !data.artworks.some((artwork) =>
      artwork.status === "em_analise" ||
      artwork.analysis?.state === "queued" ||
      artwork.analysis?.state === "processing"
    )) return;
    const timer = window.setTimeout(() => void refresh(), 2500);
    return () => window.clearTimeout(timer);
  }, [data.artworks, refresh, session]);
  const run = async (action: () => Promise<unknown>) => {
    setError(null);
    try {
      await action();
      await refresh();
    } catch (e) {
      const message =
        e instanceof Error ? e.message : "Operação não concluída.";
      setError(message);
      throw e;
    }
  };
  const value: StoreValue = {
    session,
    data,
    loading,
    error,
    login: () => setSession({ name: "Ana Costa", role: "creator" }),
    logout: () => {
      setSession(null);
      setData({ projects: [], artworks: [] });
    },
    switchRole: () =>
      setSession((s) =>
        s
          ? {
              name: s.role === "creator" ? "Rafael Martins" : "Ana Costa",
              role: s.role === "creator" ? "reviewer" : "creator",
            }
          : null,
      ),
    refresh,
    createProject: async (name, briefing) => {
      if (!session) throw new Error("Sessão ausente.");
      const id = await createProjectApi(session.role, name, briefing);
      await refresh();
      return id;
    },
    extractBriefing: async (file) => {
      if (!session) throw new Error("Sessão ausente.");
      return extractBriefingApi(session.role, file);
    },
    addArtwork: async (projectId, input, file) => {
      if (!session) throw new Error("Sessão ausente.");
      await run(() => uploadArtworkApi(session.role, projectId, input, file));
    },
    addArtworkVersion: async (artworkId, file) => {
      if (!session) throw new Error("Sessão ausente.");
      await run(() => uploadArtworkVersionApi(session.role, artworkId, file));
    },
    generateTemplates: async (projectId, channels) => {
      if (!session) throw new Error("Sessão ausente.");
      await run(() => generateTemplatesApi(session.role, projectId, channels));
    },
    previewTemplate: async (artworkId, templateData) => {
      if (!session) throw new Error("Sessão ausente.");
      return previewTemplateApi(session.role, artworkId, templateData);
    },
    saveTemplate: async (artworkId, templateData) => {
      if (!session) throw new Error("Sessão ausente.");
      await run(() => saveTemplateApi(session.role, artworkId, templateData));
    },
    analyzeArtwork: async (artworkId) => {
      if (!session) throw new Error("Sessão ausente.");
      await run(() => analyzeArtworkApi(session.role, artworkId));
    },
    submitArtwork: async (id) => {
      if (!session) throw new Error("Sessão ausente.");
      await run(() => submitArtworkApi(session.role, id));
    },
    approveArtwork: async (id) => {
      if (!session) throw new Error("Sessão ausente.");
      await run(() => approveArtworkApi(session.role, id));
    },
    returnArtwork: async (id, comment) => {
      if (!session) throw new Error("Sessão ausente.");
      await run(() => returnArtworkApi(session.role, id, comment));
    },
    projectById: (id) => data.projects.find((p) => p.id === id),
    artworkById: (id) => data.artworks.find((a) => a.id === id),
  };
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
// eslint-disable-next-line react-refresh/only-export-components
export function useAppStore() {
  const context = useContext(Context);
  if (!context) throw new Error("Store ausente");
  return context;
}
