import type { Artwork, Briefing, BriefingExtraction, Project, Role, TemplateData } from '../domain/types'

const API = '/api/v1'
const userId = (role: Role) => role === 'reviewer' ? 'rafael' : 'ana'

interface BackendArtwork { id:number; projeto_id:number; nome:string; canal:string; canal_nome:string; status:string; imagem_url?:string; versao_atual?:number; ultima_revisao?:{comentario?:string};historico?:Array<{id:string;em:string;ator:string;papel:'criador'|'revisor';acao:string;comentario?:string}>;template_editavel?:boolean;template_dados?:{produto:string;preco_centavos?:number;objetivo:string;informacoes_obrigatorias:string};analise?:{estado:'queued'|'processing'|'completed'|'failed'|'concluida'|'erro';erro?:string;notas:string[];achados:Array<{id:number;ordem?:number;tipo:string;titulo:string;descricao:string;referencia?:string;observado?:string;esperado?:string;confianca?:number;regiao?:{nx:number;ny:number;nw:number;nh:number}}> } }
interface BackendProject { id:number; nome:string; objetivo?:string; descricao?:string; prazo?:string; produto?:string; preco?:string; informacoes_obrigatorias?:string; canais?:Array<{canal:string;nome:string}>; artes?:BackendArtwork[]; atualizado_em:string; tem_briefing?:boolean; briefing_nome?:string }

async function request<T>(path:string, role:Role, init:RequestInit={}):Promise<T>{
  const headers = new Headers(init.headers)
  headers.set('X-Demo-User', userId(role))
  if(init.body && !(init.body instanceof FormData)) headers.set('Content-Type','application/json')
  const response=await fetch(`${API}${path}`,{...init,headers})
  if(!response.ok){const body=await response.json().catch(()=>({detail:'Falha de comunicação com o backend.'}));throw new Error(body.detail||body.message||`Erro HTTP ${response.status}`)}
  return response.json() as Promise<T>
}
const status=(value:string):Artwork['status']=>value==='precisa_ajustes'?'precisa_de_ajustes':value as Artwork['status']
const mapProject=(raw:BackendProject):Project=>({id:String(raw.id),name:raw.nome,createdAt:raw.atualizado_em,artworkIds:(raw.artes||[]).map(a=>String(a.id)),briefing:{objective:raw.objetivo||'',description:raw.descricao||'',deadline:raw.prazo,product:raw.produto||'',price:raw.preco?`R$ ${raw.preco}`:'',requiredText:raw.informacoes_obrigatorias||'',channels:(raw.canais||[]).map(c=>c.nome),source:raw.tem_briefing?'document_pending_transcription':'manual',sourceFileName:raw.briefing_nome}})
const brl=(cents?:number)=>cents===undefined||cents===null?'':(cents/100).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2})
const mapArtwork=(raw:BackendArtwork):Artwork=>({id:String(raw.id),projectId:String(raw.projeto_id),name:raw.nome,channel:raw.canal_nome||raw.canal,fileName:raw.nome,previewDataUrl:raw.imagem_url?`${raw.imagem_url}?demo_user=ana`:undefined,status:status(raw.status),comments:raw.ultima_revisao?.comentario?[raw.ultima_revisao.comentario]:[],history:(raw.historico||[]).map(item=>({id:item.id,at:item.em,actor:item.ator,role:item.papel==='revisor'?'reviewer':'creator',action:item.acao,comment:item.comentario})),analysis:raw.analise?{state:raw.analise.estado,error:raw.analise.erro,notes:raw.analise.notas||[],findings:(raw.analise.achados||[]).map((item,index)=>({id:item.id,order:item.ordem||index+1,type:item.tipo,title:item.titulo,description:item.descricao,reference:item.referencia,observed:item.observado,expected:item.esperado,confidence:item.confianca,region:item.regiao}))}:undefined,templateData:raw.template_editavel&&raw.template_dados?{product:raw.template_dados.produto,price:brl(raw.template_dados.preco_centavos),objective:raw.template_dados.objetivo,requiredText:raw.template_dados.informacoes_obrigatorias}:undefined})

export async function loadData(role:Role){
  const summaries=await request<BackendProject[]>('/projetos',role)
  const details=await Promise.all(summaries.map(p=>request<BackendProject>(`/projetos/${p.id}`,role)))
  const listed=details.flatMap(p=>p.artes||[])
  const artworks=await Promise.all(listed.map(art=>request<BackendArtwork>(`/artes/${art.id}`,role)))
  return {projects:details.map(mapProject),artworks:artworks.map(mapArtwork)}
}
export async function createProjectApi(role:Role,name:string,briefing:Briefing){
  const channels:Record<string,string>={'Instagram Feed':'instagram_feed','Instagram Stories':'instagram_stories','WhatsApp':'whatsapp','Banner do site':'banner_site'}
  const raw=await request<BackendProject>('/projetos',role,{method:'POST',body:JSON.stringify({nome:name,objetivo:briefing.objective,descricao:briefing.description,prazo:briefing.deadline||null,produto:briefing.product,preco:briefing.price,informacoes_obrigatorias:briefing.requiredText,canais:briefing.channels.map(c=>channels[c]).filter(Boolean),briefing_token:briefing.sourceToken||null})})
  return String(raw.id)
}
interface ExtractedField{valor?:string|string[];estado:string}
interface ExtractedBriefing{token:string;avisos:string[];campos:Record<string,ExtractedField>}
export async function extractBriefingApi(role:Role,file:File):Promise<BriefingExtraction>{const form=new FormData();form.append('file',file);const raw=await request<ExtractedBriefing>('/briefings/extrair',role,{method:'POST',body:form});const value=(key:string)=>raw.campos[key]?.estado==='found'?raw.campos[key].valor:undefined;const channelNames:Record<string,string>={instagram_feed:'Instagram Feed',instagram_stories:'Instagram Stories',whatsapp:'WhatsApp',banner_site:'Banner do site'};return {token:raw.token,campaignName:value('nome_campanha') as string|undefined,product:value('produto') as string|undefined,price:value('preco') as string|undefined,objective:value('objetivo') as string|undefined,deadline:value('prazo') as string|undefined,requiredText:value('informacoes_obrigatorias') as string|undefined,channels:((value('canais') as string[]|undefined)||[]).map(channel=>channelNames[channel]).filter(Boolean),warnings:raw.avisos||[]}}
export async function uploadArtworkApi(role:Role,projectId:string,input:Pick<Artwork,'name'|'channel'>,file:File){const channels:Record<string,string>={'Instagram Feed':'instagram_feed','Instagram Stories':'instagram_stories','WhatsApp':'whatsapp','Banner do site':'banner_site'};const form=new FormData();form.append('file',file);return request<BackendArtwork>(`/projetos/${projectId}/artes?canal=${channels[input.channel]||input.channel}`,role,{method:'POST',body:form})}
export async function uploadArtworkVersionApi(role:Role,artworkId:string,file:File){const form=new FormData();form.append('file',file);return request<BackendArtwork>(`/artes/${artworkId}/versoes`,role,{method:'POST',body:form})}
export const generateTemplatesApi=(role:Role,projectId:string,channels:string[])=>request(`/projetos/${projectId}/templates`,role,{method:'POST',body:JSON.stringify({canais:channels})})
const templateBody=(data:TemplateData)=>({produto:data.product,preco:data.price,objetivo:data.objective,informacoes_obrigatorias:data.requiredText})
export async function previewTemplateApi(role:Role,id:string,data:TemplateData){const response=await fetch(`${API}/artes/${id}/template/preview`,{method:'POST',headers:{'X-Demo-User':userId(role),'Content-Type':'application/json'},body:JSON.stringify(templateBody(data))});if(!response.ok){const body=await response.json().catch(()=>({detail:'Não foi possível gerar a prévia.'}));throw new Error(body.detail)}return response.blob()}
export const saveTemplateApi=(role:Role,id:string,data:TemplateData)=>request(`/artes/${id}/template/versoes`,role,{method:'POST',body:JSON.stringify(templateBody(data))})
export const analyzeArtworkApi=(role:Role,id:string)=>request(`/artes/${id}/analise`,role,{method:'POST'})
export const submitArtworkApi=(role:Role,id:string)=>request(`/artes/${id}/enviar-aprovacao`,role,{method:'POST'})
export const approveArtworkApi=(role:Role,id:string)=>request(`/artes/${id}/aprovar`,role,{method:'POST'})
export const returnArtworkApi=(role:Role,id:string,comment:string)=>request(`/artes/${id}/solicitar-ajustes`,role,{method:'POST',body:JSON.stringify({comentario:comment})})
