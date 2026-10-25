from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variáveis de ambiente (ex.: OCR_MOTOR=paddle) sobrescrevem estes padrões."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Infra ---
    database_url: str = "sqlite:////data/cria_mais.db"
    data_dir: str = "/data"
    cors_origins: list[str] = ["http://localhost", "http://localhost:5173"]

    # --- Uploads ---
    max_briefing_mb: int = 20                 # design: "até 20 MB"
    max_arte_mb: int = 20
    extensoes_briefing: list[str] = [".pdf", ".docx", ".txt"]
    tipos_arte: list[str] = ["image/jpeg", "image/png", "image/webp"]

    # --- Usuários de demonstração (header X-Usuario) ---
    usuarios: dict[str, dict] = {
        "ana": {"nome": "Ana Costa", "papel": "designer", "cargo": "Designer • Marketing"},
        "bruno": {"nome": "Bruno Lima", "papel": "designer", "cargo": "Designer • Marketing"},
        "rafael": {"nome": "Rafael Martins", "papel": "revisor", "cargo": "Revisor de marketing"},
    }

    # --- OCR (PaddleOCR) ---
    ocr_motor: str = "paddle"
    ocr_lang: str = "latin"          # confirme no 1º teste real (cobre português)
    ocr_confianca_min: float = 0.6

    # --- Ortografia (LanguageTool local) ---
    languagetool_url: str = "http://languagetool:8010"
    languagetool_lang: str = "pt-BR"
    languagetool_timeout: float = 20.0
    ortografia_ignorar: list[str] = []   # marcas e termos que não devem ser corrigidos

    # --- Regras de conferência ---
    margem_minima_pct: float = 0.04      # distância mínima do texto à borda (% do menor lado)

    # --- Outpainting (IOPaint) ---
    outpainting_ativo: bool = False
    iopaint_url: str = "http://iopaint:8080"
    iopaint_timeout: float = 600.0
    outpainting_max_extensao: float = 1.0   # no máximo +100% numa dimensão
    # defaults usados pelo código do outro dev quando nenhuma proporção é passada
    proporcao_largura: int = 1
    proporcao_altura: int = 1
    tolerancia_proporcao: float = 0.01

    # --- Ollama / visão (OPCIONAL, fora do fluxo principal) ---
    ollama_url: str = "http://ollama:11434"
    modelo_visao: str = "llava"
    modelo_ocr: str = "deepseek-ocr"
    ollama_timeout: float = 180.0

    @property
    def max_briefing_bytes(self) -> int:
        return self.max_briefing_mb * 1024 * 1024

    @property
    def max_arte_bytes(self) -> int:
        return self.max_arte_mb * 1024 * 1024


settings = Settings()