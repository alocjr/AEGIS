export interface CoursePublic {
  slug: string
  titulo?: string
  tema?: string
  trilha?: string
  publico?: string
  objetivo?: string
  num_encontros?: number
  num_semanas?: number
  programa_formacao_executiva?: ProgramaFormacaoExecutiva
  [key: string]: unknown
}

/** Material de apoio de um encontro */
export interface MaterialSuporte {
  item: string
  url?: string
}

/** Encontro (etapa) da jornada */
export interface Encontro {
  id: number
  /** ObjectId do quiz deste encontro (quando existe quiz). */
  quiz_id?: string
  titulo?: string
  subtitulo?: string
  tema?: string
  objetivos?: string[]
  resultados_esperados?: string[]
  material_suporte?: MaterialSuporte[]
}

/** Semana da jornada de aprendizagem */
export interface JornadaSemana {
  semana: number
  tema_central?: string
  encontros?: Encontro[]
}

/** Bloco da metodologia (estrutura do encontro) */
export interface EstruturaEncontro {
  duracao?: string
  bloco?: string
  descricao?: string
}

/** Entregável resumido */
export interface EntregavelResumo {
  item?: string
  origem?: string
}

/** Programa completo retornado pela API pública ao carregar trilha por slug */
export interface ProgramaFormacaoExecutiva {
  cabecalho?: {
    titulo?: string
    tema?: string
    publico?: string
    trilha?: string
    estrutura_resumo?: string
    ano?: string
  }
  visao_geral?: {
    objetivo?: string
    instrutor?: string
  }
  jornada_aprendizagem?: JornadaSemana[]
  metodologia_detalhada?: {
    estrutura_encontro?: EstruturaEncontro[]
  }
  entregaveis_resumo?: EntregavelResumo[]
}

export interface ApiError {
  detail: string | { msg: string; loc?: string[] }[]
}
