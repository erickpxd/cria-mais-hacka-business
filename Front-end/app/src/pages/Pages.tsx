import { ChangeEvent, FormEvent, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import type { ArtworkStatus, Briefing } from "../domain/types";
import {
  Button,
  CampaignPreview,
  PageTitle,
  Shell,
  StatusPill,
} from "../components/Layout";
import { useAppStore } from "../store/AppStore";
import criaMaisLogo from "../assets/cria-mais-logo.png";

const emptyBriefing: Briefing = {
  objective: "",
  description: "",
  product: "",
  price: "",
  requiredText: "",
  channels: ["Instagram Feed"],
  source: "manual",
};

export function LoginPage() {
  const { session, login } = useAppStore();
  const navigate = useNavigate();
  const [filled, setFilled] = useState(false);
  if (session) return <Navigate to="/" replace />;
  const enter = () => {
    setFilled(true);
    window.setTimeout(() => {
      login();
      navigate("/");
    }, 250);
  };
  return (
    <div className="login-page">
      <section className="login-card">
        <div className="brand login-brand">
          <img src={criaMaisLogo} alt="CriaMais — Mais tempo. Mais resultado." />
        </div>
        <div className="login-art">
          <span>CRIAÇÃO</span>
          <h1>Boas ideias ganham cor.</h1>
          <p>Organize briefings, artes e aprovações em uma jornada simples.</p>
        </div>
        <div className="login-form">
          <span className="eyebrow">AMBIENTE DE POC</span>
          <h2>Entre na demonstração</h2>
          <p>
            Use uma conta fictícia para explorar as jornadas de Criador e
            Revisor.
          </p>
          <label className="field">
            <b>Conta demonstrativa</b>
            <input
              readOnly
              value={filled ? "ana.costa@demonstracao.local" : ""}
              placeholder="Preenchida automaticamente"
            />
          </label>
          <Button onClick={enter}>Entrar na demonstração</Button>
          <small>Ambiente demonstrativo — sem autenticação real.</small>
        </div>
      </section>
    </div>
  );
}

export function HomePage() {
  const { data, session } = useAppStore();
  const creator = session?.role === "creator";
  const adjustments = data.artworks.filter(
    (a) => a.status === "precisa_de_ajustes",
  ).length;
  const approvals = data.artworks.filter(
    (a) => a.status === "aguardando_aprovacao",
  ).length;
  return (
    <Shell>
      <PageTitle
        eyebrow={creator ? "SEU ESPAÇO DE CRIAÇÃO" : "ESPAÇO DE REVISÃO"}
        title={
          creator
            ? "Olá! Vamos colocar as campanhas em dia?"
            : "Olá! Vamos revisar as entregas?"
        }
        subtitle="Os números abaixo refletem a mesma fonte de dados local."
        action={
          creator ? (
            <Link className="button primary" to="/projetos/novo">
              + Novo projeto
            </Link>
          ) : (
            <Link className="button primary" to="/aprovacoes">
              Ver aprovações
            </Link>
          )
        }
      />
      <div className="attention-grid">
        <InfoCard value={adjustments} label="artes precisam de ajustes" />
        <InfoCard value={approvals} label="artes aguardam aprovação" />
        <InfoCard value={data.projects.length} label="projetos disponíveis" />
      </div>
      <div className="section-title">
        <h2>Projetos recentes</h2>
        <Link className="button secondary" to="/projetos">
          Ver todos →
        </Link>
      </div>
      <div className="project-grid">
        {data.projects.slice(0, 3).map((project) => (
          <ProjectCard key={project.id} projectId={project.id} />
        ))}
      </div>
    </Shell>
  );
}
function InfoCard({ value, label }: { value: number; label: string }) {
  return (
    <article className="info-card">
      <div>
        <span className="metric">{value}</span>
        <b>{label}</b>
      </div>
      <small>Atualizado pelas ações realizadas nesta demonstração.</small>
    </article>
  );
}
function ProjectCard({ projectId }: { projectId: string }) {
  const { projectById, data } = useAppStore();
  const project = projectById(projectId);
  if (!project) return null;
  const arts = data.artworks.filter((a) => a.projectId === project.id);
  const status: ArtworkStatus = arts.some(
    (a) => a.status === "precisa_de_ajustes",
  )
    ? "precisa_de_ajustes"
    : arts.some((a) => a.status === "aguardando_aprovacao")
      ? "aguardando_aprovacao"
      : arts.length && arts.every((a) => a.status === "aprovada")
        ? "aprovada"
        : "em_producao";
  return (
    <Link className="project-card" to={`/projetos/${project.id}`}>
      <div className="project-cover lilac">
        <span>
          <small>
            PROJETO PERSISTIDO NA POC
          </small>
          <b>{project.name}</b>
        </span>
        {arts[0] && (
          <CampaignPreview
            briefing={project.briefing}
            imageUrl={arts[0].previewDataUrl}
            compact
          />
        )}
      </div>
      <div className="project-info">
        <StatusPill status={status} />
        <h3>{project.name}</h3>
        <small>{project.briefing.objective}</small>
        <div>
          <span>{arts.length} arte(s)</span>
          <span>{project.briefing.channels.length} canal(is)</span>
        </div>
      </div>
    </Link>
  );
}

export function ProjectsPage() {
  const { data } = useAppStore();
  const [query, setQuery] = useState("");
  const shown = data.projects.filter((p) =>
    p.name.toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <Shell>
      <PageTitle
        title="Projetos"
        subtitle="Projetos e briefings vêm da fonte única de dados da POC."
        action={
          <Link className="button primary" to="/projetos/novo">
            + Novo projeto
          </Link>
        }
      />
      <div className="toolbar">
        <b>{shown.length} projeto(s)</b>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar projetos"
          aria-label="Buscar projetos"
        />
      </div>
      {shown.length ? (
        <div className="project-grid">
          {shown.map((p) => (
            <ProjectCard key={p.id} projectId={p.id} />
          ))}
        </div>
      ) : (
        <Empty
          title="Nenhum projeto encontrado"
          text="Tente outro termo ou crie um projeto."
        />
      )}
    </Shell>
  );
}

export function NewProjectPage() {
  const { createProject, extractBriefing } = useAppStore();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [briefing, setBriefing] = useState(emptyBriefing);
  const [documentName, setDocumentName] = useState("");
  const [documentWarnings, setDocumentWarnings] = useState<string[]>([]);
  const update = (key: keyof Briefing, value: string | string[]) =>
    setBriefing((b) => ({ ...b, [key]: value }));
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !briefing.objective.trim() || !briefing.product.trim())
      return;
    try {
      const projectId = await createProject(name.trim(), briefing);
      navigate(`/projetos/${projectId}`);
    } catch {
      // O Shell apresenta a mensagem devolvida pela API e mantém o formulário preenchido.
    }
  };
  const document = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!["pdf", "docx", "txt"].includes(ext || "")) {
      setDocumentName("Formato inválido. Use PDF, DOCX ou TXT.");
      return;
    }
    setDocumentName(`Extraindo dados de ${file.name}…`);
    setDocumentWarnings([]);
    try {
      const extraction = await extractBriefing(file);
      if (!name.trim() && extraction.campaignName) setName(extraction.campaignName);
      setBriefing((b) => ({
        ...b,
        objective: extraction.objective || b.objective,
        product: extraction.product || b.product,
        price: extraction.price || b.price,
        deadline: extraction.deadline || b.deadline,
        requiredText: extraction.requiredText || b.requiredText,
        channels: extraction.channels.length ? extraction.channels : b.channels,
        source: "document_pending_transcription",
        sourceFileName: file.name,
        sourceToken: extraction.token,
      }));
      setDocumentName(`${file.name} — revise e confirme os campos abaixo.`);
      setDocumentWarnings(extraction.warnings);
    } catch (error) {
      setDocumentName(error instanceof Error ? error.message : "Não foi possível ler o documento.");
    }
  };
  return (
    <Shell>
      <div className="breadcrumbs">
        <Link to="/projetos">Projetos</Link> › Novo projeto
      </div>
      <PageTitle
        title="Vamos criar seu projeto"
        subtitle="Cadastre manualmente ou extraia campos de um documento e confirme os dados da campanha."
      />
      <div className="document-honesty">
        <b>Documento opcional</b>
        <p>
          PDF, DOCX ou TXT são lidos por regras determinísticas. Revise todos os
          campos antes de criar o projeto; dados ausentes não são inventados.
        </p>
        <label className="button secondary">
          Selecionar PDF, DOCX ou TXT
          <input
            hidden
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={document}
          />
        </label>
        {documentName && <span>{documentName}</span>}
        {documentWarnings.map((warning) => <small key={warning}>{warning}</small>)}
      </div>
      <form className="manual-grid poc-form" onSubmit={submit}>
        <section className="panel form-panel">
          <h2>01 Campanha</h2>
          <Field label="Nome do projeto *" value={name} onChange={setName} />
          <Field
            label="Objetivo *"
            value={briefing.objective}
            onChange={(v) => update("objective", v)}
          />
          <Field
            label="Descrição"
            textarea
            value={briefing.description}
            onChange={(v) => update("description", v)}
          />
          <Field
            label="Prazo"
            type="date"
            value={briefing.deadline || ""}
            onChange={(v) => update("deadline", v)}
          />
        </section>
        <section className="panel form-panel">
          <h2>02 Produto e conteúdo</h2>
          <Field
            label="Produto *"
            value={briefing.product}
            onChange={(v) => update("product", v)}
          />
          <Field
            label="Preço informado"
            value={briefing.price}
            onChange={(v) => update("price", v)}
          />
          <Field
            label="Informação obrigatória"
            textarea
            value={briefing.requiredText}
            onChange={(v) => update("requiredText", v)}
          />
        </section>
        <section className="panel form-panel">
          <h2>03 Canais</h2>
          {[
            "Instagram Feed",
            "Instagram Stories",
            "WhatsApp",
            "Banner do site",
          ].map((channel) => (
            <label className="check" key={channel}>
              <input
                type="checkbox"
                checked={briefing.channels.includes(channel)}
                onChange={() =>
                  update(
                    "channels",
                    briefing.channels.includes(channel)
                      ? briefing.channels.filter((c) => c !== channel)
                      : [...briefing.channels, channel],
                  )
                }
              />
              <span>
                <b>{channel}</b>
              </span>
            </label>
          ))}
        </section>
        <div className="form-actions">
          <Link className="button secondary" to="/projetos">
            Cancelar
          </Link>
          <small>Campos com * são obrigatórios.</small>
          <Button
            type="submit"
            disabled={
              !name.trim() ||
              !briefing.objective.trim() ||
              !briefing.product.trim()
            }
          >
            Criar projeto
          </Button>
        </div>
      </form>
    </Shell>
  );
}
function Field({
  label,
  value,
  onChange,
  textarea,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  textarea?: boolean;
  type?: string;
}) {
  return (
    <label className="field">
      <b>{label}</b>
      {textarea ? (
        <textarea value={value} onChange={(e) => onChange(e.target.value)} />
      ) : (
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
    </label>
  );
}

export function ProjectDetailPage() {
  const { id } = useParams();
  const { projectById, data, addArtwork, addArtworkVersion, submitArtwork, loading } = useAppStore();
  const project = id ? projectById(id) : undefined;
  const [feedback, setFeedback] = useState("");
  if (loading && !project)
    return <Shell><div className="empty"><p>Carregando projeto…</p></div></Shell>;
  if (!project) return <Navigate to="/projetos" replace />;
  const arts = data.artworks.filter((a) => a.projectId === project.id);
  const addFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!["image/png", "image/jpeg"].includes(file.type)) {
      setFeedback("Formato inválido. Envie PNG ou JPG.");
      return;
    }
    try {
      await addArtwork(
        project.id,
        {
          name: file.name.replace(/\.[^.]+$/, ""),
          channel: project.briefing.channels[0] || "Instagram Feed",
        },
        file,
      );
      setFeedback("Arte adicionada e persistida no backend.");
    } catch {
      setFeedback("Não foi possível adicionar a arte. Consulte o erro exibido acima.");
    }
  };
  const submit = async (artId: string, message: string) => {
    try {
      await submitArtwork(artId);
      setFeedback(message);
    } catch {
      setFeedback("Não foi possível enviar a arte. Consulte o erro exibido acima.");
    }
  };
  const addVersion = async (artId: string, e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!["image/png", "image/jpeg"].includes(file.type)) {
      setFeedback("Formato inválido. Envie PNG ou JPG.");
      return;
    }
    try {
      await addArtworkVersion(artId, file);
      setFeedback("Nova versão vinculada à arte. Aguarde a conferência antes de reenviar.");
    } catch {
      setFeedback("Não foi possível criar a versão. Consulte o erro exibido acima.");
    }
  };
  return (
    <Shell>
      <div className="breadcrumbs">
        <Link to="/projetos">Projetos</Link> › {project.name}
      </div>
      <PageTitle
        title={project.name}
        subtitle="Projeto persistido no backend da demonstração."
        action={<div className="page-actions">
          <label className="button primary">
            + Enviar arte para validar
            <input hidden type="file" accept="image/png,image/jpeg" onChange={addFile} />
          </label>
        </div>}
      />
      {feedback && (
        <div
          className={
            feedback.includes("inválido") || feedback.includes("Não foi")
              ? "error-banner"
              : "success"
          }
        >
          {feedback}
        </div>
      )}
      <section className="briefing-summary">
        <div>
          <span className="eyebrow">BRIEFING</span>
          <h2>{project.briefing.objective}</h2>
          <p>{project.briefing.description || "Sem descrição."}</p>
        </div>
        <dl>
          <div>
            <dt>Produto</dt>
            <dd>{project.briefing.product}</dd>
          </div>
          <div>
            <dt>Preço</dt>
            <dd>{project.briefing.price || "Não informado"}</dd>
          </div>
          <div>
            <dt>Prazo</dt>
            <dd>{project.briefing.deadline || "Não informado"}</dd>
          </div>
          <div>
            <dt>Origem</dt>
            <dd>
              {project.briefing.source === "manual"
                ? "Preenchimento manual"
                : "Documento aguardando transcrição manual"}
            </dd>
          </div>
        </dl>
      </section>
      <div className="section-title">
        <h2>Artes ({arts.length})</h2>
      </div>
      {arts.length ? (
        <div className="art-grid">
          {arts.map((art) => (
            <article className="art-card" key={art.id}>
              <Link to={`/artes/${art.id}`}>
                <CampaignPreview
                  briefing={project.briefing}
                  imageUrl={art.previewDataUrl}
                />
              </Link>
              <div>
                <b>{art.name}</b>
                <small>
                  {art.channel}
                  <span>{art.fileName}</span>
                </small>
                <StatusPill status={art.status} />
                {art.status === "em_producao" && (
                  <Button
                    onClick={() => void submit(art.id, "Arte enviada para a fila de aprovação.")}
                  >
                    Enviar para aprovação
                  </Button>
                )}
                {art.status === "precisa_de_ajustes" && (
                  <>
                    <p className="review-note">
                      Comentário do revisor: {art.comments.at(-1)}
                    </p>
                    <label className="button primary">
                      Enviar nova versão
                      <input hidden type="file" accept="image/png,image/jpeg" onChange={(e) => void addVersion(art.id, e)} />
                    </label>
                    <Button
                      variant="secondary"
                      onClick={() => void submit(art.id, "Versão atual enviada ao revisor.")}
                    >
                      Reenviar versão atual
                    </Button>
                  </>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Empty
          title="Nenhuma arte neste projeto"
          text="Adicione uma imagem PNG ou JPG. Ela ficará vinculada somente a este projeto."
        />
      )}
      <div className="notice">
        <span>
          <b>Validação de conformidade da arte</b>
          <small>
            A conferência compara a arte pronta com o briefing e as regras configuradas
            para Pague Menos: paleta, logo, conteúdo, margens e legibilidade.
          </small>
        </span>
      </div>
    </Shell>
  );
}

export function ArtworkPage() {
  const { id } = useParams();
  const { artworkById, projectById, data, loading, analyzeArtwork } = useAppStore();
  const art = id ? artworkById(id) : undefined;
  const project = art ? projectById(art.projectId) : undefined;
  if ((!art || !project) && (loading || data.projects.length === 0))
    return <Shell><div className="empty"><p>Carregando arte…</p></div></Shell>;
  if (!art || !project) return <Navigate to="/projetos" replace />;
  const processing = ["queued", "processing"].includes(art.analysis?.state || "");
  const completed = ["completed", "concluida"].includes(art.analysis?.state || "");
  const failed = ["failed", "erro"].includes(art.analysis?.state || "");
  const findings = art.analysis?.findings || [];
  const headline = processing
    ? "Estamos conferindo sua arte…"
    : completed && findings.length > 0
      ? `Encontramos ${findings.length} ${findings.length === 1 ? "ponto" : "pontos"} para revisar.`
      : completed
        ? "Conferência concluída."
        : "Confira esta versão da arte";
  const subtitle = processing
    ? "Comparando o conteúdo da peça com o briefing associado ao projeto."
    : completed && findings.length > 0
      ? "Confira os pontos identificados antes de preparar uma nova versão."
      : completed
        ? "As regras executadas não encontraram divergências nesta versão. A revisão humana continua necessária."
        : "Execute a conferência para verificar identidade de marca, conteúdo e normas da peça.";
  return (
    <Shell>
      <div className="breadcrumbs">
        <Link to={`/projetos/${project.id}`}>{project.name}</Link> › {art.name}
      </div>
      <PageTitle
        title={headline}
        subtitle={subtitle}
        action={<Link className="button secondary" to={`/projetos/${project.id}`}>Ver briefing</Link>}
      />
      <div className="analysis-workspace">
        <div className="analysis-viewer">
          <div className="analysis-viewer-head">
            <b>{project.briefing.product || art.name}</b>
            <span className={`analysis-state ${processing ? "processing" : findings.length ? "has-findings" : "clean"}`}>
              {processing ? "• Em análise" : findings.length ? `• ${findings.length} ${findings.length === 1 ? "ajuste" : "ajustes"}` : "• Conferida"}
            </span>
          </div>
          <div className="analysis-image">
            {art.previewDataUrl
              ? <img src={art.previewDataUrl} alt="Arte submetida à conferência" />
              : <CampaignPreview briefing={project.briefing} />}
            {completed && findings.map((finding) => finding.region && (
              <span
                className="finding-marker"
                key={finding.id}
                title={finding.title}
                style={{
                  left: `${Math.min(96, Math.max(4, (finding.region.nx + finding.region.nw / 2) * 100))}%`,
                  top: `${Math.min(96, Math.max(4, (finding.region.ny + finding.region.nh / 2) * 100))}%`,
                }}
              >{finding.order}</span>
            ))}
          </div>
          <div className="analysis-meta"><span>Versão atual • {art.channel}</span><span>Original preservado</span></div>
        </div>
        <aside className="analysis-findings">
          {!art.analysis && <div className="analysis-start-card">
            <span className="analysis-pulse">•••</span>
            <h2>Uma conferência a mais para sua criação.</h2>
            <p>O arquivo original será mantido. Nenhuma alteração é aplicada sem sua revisão.</p>
            <Button onClick={() => void analyzeArtwork(art.id)}>Executar conferência</Button>
          </div>}
          {processing && <div className="analysis-start-card">
            <span className="analysis-pulse">● ● ●</span>
            <h2>Uma conferência a mais para sua criação.</h2>
            <p>O arquivo original será mantido. Nenhuma alteração é aplicada sem sua revisão.</p>
            <div className="analysis-steps"><span className="done">✓</span><b>Briefing e regras associados</b><span className="spinning">◌</span><b>Conferindo paleta, logo, conteúdo e margens</b><span>○</span><b>Preparando correções propostas</b></div>
          </div>}
          {failed && <div className="analysis-start-card error-card">
            <h2>Conferência indisponível</h2>
            <p>{art.analysis?.error || "Não foi possível processar esta versão."}</p>
            <Button variant="secondary" onClick={() => void analyzeArtwork(art.id)}>Tentar novamente</Button>
          </div>}
          {completed && findings.length === 0 && <div className="analysis-start-card clean-card">
            <span className="analysis-check">✓</span>
            <h2>Nenhuma inconsistência detectada</h2>
            <p>As regras configuradas de marca, conteúdo e geometria não encontraram divergências. Isso não substitui a revisão humana.</p>
          </div>}
          {completed && findings.map((finding) => (
            <article className={`finding-card ${finding.type === "preco_divergente" ? "critical" : "attention"}`} key={finding.id}>
              <div className="finding-title"><span>• {finding.order}</span><h3>{finding.title}</h3></div>
              {finding.observed && finding.expected && <div className="finding-comparison">
                <div><small>{finding.type === "preco_divergente" ? "Na arte" : "Encontrado"}</small><b>{finding.type === "preco_divergente" ? `R$ ${finding.observed}` : finding.observed}</b></div>
                <i>→</i>
                <div><small>{finding.type === "preco_divergente" ? "No briefing" : "Sugestão"}</small><b>{finding.type === "preco_divergente" ? `R$ ${finding.expected}` : finding.expected}</b></div>
              </div>}
              <p>{finding.description}</p>
              {finding.reference && <small className="finding-reference">Referência: {finding.reference}</small>}
              {finding.confidence !== undefined && <small className="finding-confidence">Confiança da verificação: {Math.round(finding.confidence * 100)}%</small>}
            </article>
          ))}
          {completed && art.analysis?.notes.map((note) => <p className="analysis-note" key={note}>ⓘ {note}</p>)}
          {completed && <p className="analysis-human-note">ⓘ As sugestões precisam da avaliação de uma pessoa.</p>}
        </aside>
      </div>
      <div className="analysis-actions">
        <Link className="button secondary" to={`/projetos/${project.id}`}>← Voltar ao projeto</Link>
      </div>
      <details className="analysis-history"><summary>Histórico da arte</summary>{art.history.map((item) => (
        <div className="history-row" key={item.id}><b>{item.action}</b><small>{item.actor} • {item.role === "creator" ? "Criador" : "Revisor"}</small>{item.comment && <p>{item.comment}</p>}</div>
      ))}</details>
    </Shell>
  );
}

export function ApprovalsPage() {
  const { data, projectById } = useAppStore();
  const pending = data.artworks.filter(
    (a) => a.status === "aguardando_aprovacao",
  );
  return (
    <Shell>
      <PageTitle
        title="Aguardando sua aprovação"
        subtitle={`${pending.length} arte(s) enviada(s) pelo Criador.`}
      />
      {pending.length ? (
        <div className="approval-list">
          {pending.map((art) => {
            const project = projectById(art.projectId);
            if (!project) return null;
            return (
              <article key={art.id}>
                <div className="thumb">
                  <CampaignPreview
                    briefing={project.briefing}
                    imageUrl={art.previewDataUrl}
                    compact
                  />
                </div>
                <div>
                  <h3>{art.name}</h3>
                  <p>{project.name}</p>
                  <small>{art.fileName}</small>
                </div>
                <dl>
                  <div>
                    <dt>CANAL</dt>
                    <dd>{art.channel}</dd>
                  </div>
                  <div>
                    <dt>STATUS</dt>
                    <dd>
                      <StatusPill status={art.status} />
                    </dd>
                  </div>
                </dl>
                <Link className="button secondary" to={`/aprovacoes/${art.id}`}>
                  Avaliar arte →
                </Link>
              </article>
            );
          })}
        </div>
      ) : (
        <Empty
          title="Nenhuma arte aguardando aprovação"
          text="Quando o Criador enviar uma arte, ela aparecerá aqui."
        />
      )}
    </Shell>
  );
}

export function ReviewPage() {
  const { id } = useParams();
  const { artworkById, projectById, approveArtwork, returnArtwork, loading } =
    useAppStore();
  const navigate = useNavigate();
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const art = id ? artworkById(id) : undefined;
  const project = art ? projectById(art.projectId) : undefined;
  if (loading && (!art || !project))
    return <Shell><div className="empty"><p>Carregando revisão…</p></div></Shell>;
  if (!art || !project) return <Navigate to="/aprovacoes" replace />;
  const approve = async () => {
    try {
      await approveArtwork(art.id);
      navigate("/aprovacoes");
    } catch {
      // O erro da API permanece visível no Shell.
    }
  };
  const sendBack = async () => {
    if (!comment.trim()) {
      setError("Escreva um comentário antes de devolver a arte.");
      return;
    }
    try {
      await returnArtwork(art.id, comment.trim());
      navigate("/aprovacoes");
    } catch {
      // O comentário é preservado para nova tentativa.
    }
  };
  return (
    <Shell>
      <div className="breadcrumbs">
        <Link to="/aprovacoes">Aprovações</Link> › {art.name}
      </div>
      <PageTitle
        title="Avaliar arte"
        subtitle={`${project.name} • ${art.channel}`}
      />
      <div className="review-art-grid">
        <section className="art-stage">
          <StatusPill status={art.status} />
          <CampaignPreview
            briefing={project.briefing}
            imageUrl={art.previewDataUrl}
          />
        </section>
        <aside className="panel">
          <h2>Briefing relacionado</h2>
          <p>
            <b>Objetivo:</b> {project.briefing.objective}
          </p>
          <p>
            <b>Produto:</b> {project.briefing.product}
          </p>
          <p>
            <b>Preço:</b> {project.briefing.price || "Não informado"}
          </p>
          <p>
            <b>Texto obrigatório:</b>{" "}
            {project.briefing.requiredText || "Não informado"}
          </p>
          <h2>Comentário da revisão</h2>
          <textarea
            className="review-textarea"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Obrigatório ao solicitar ajustes"
          />
          {error && <p className="error">{error}</p>}
          <div className="review-actions">
            <Button variant="danger" onClick={sendBack}>
              Solicitar ajustes
            </Button>
            <Button onClick={approve}>Aprovar arte</Button>
          </div>
        </aside>
      </div>
    </Shell>
  );
}

function Empty({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty">
      <h2>{title}</h2>
      <p>{text}</p>
    </div>
  );
}
