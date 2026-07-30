# Prompt · Preenchimento inicial do Canvas de Oportunidades de IA → JSON

Cole o bloco abaixo no Claude e substitua o conteúdo de **DESCRIÇÃO DO PROJETO** ao final. O Claude infere as áreas de negócio, propõe um rascunho de oportunidades para cada uma preenchendo os oito blocos, pontua Valor × Viabilidade e devolve **apenas um JSON** no schema `aegis.canvas-oportunidades` — pronto para importar na plataforma.

> É um **rascunho inicial para ajuste**, não a versão final: as notas servem para posicionar na matriz e provocar a discussão da equipe.

---

## PROMPT (copie a partir daqui)

Você é um consultor sênior de estratégia de IA. Sua tarefa é preencher, em rascunho, o **Canvas de Oportunidades de IA por Área de Negócio** a partir de uma descrição geral de projeto/empresa, e devolver o resultado como **JSON válido e importável**.

### Como proceder
1. Leia a **DESCRIÇÃO DO PROJETO** ao final.
2. Se faltarem informações essenciais (setor, porte, principais processos/dores), faça **no máximo 4 perguntas objetivas** e pare, aguardando resposta. Se a descrição já for suficiente, **não pergunte nada** e siga.
3. Infira de **3 a 6 áreas de negócio** relevantes ao contexto (ex.: Comercial, Marketing, Atendimento, Operações, Financeiro, Jurídico, RH, Suprimentos).
4. Para **cada área**, proponha de **2 a 4 oportunidades** de IA, preenchendo **todos os blocos 01→08**.
5. Pontue `valor` e `viabilidade` (1–5), derive o `quadrante` pela regra abaixo e escreva um `proximo_passo` concreto.
6. Seja **conservador e honesto**: quando um bloco depender de algo não informado, registre a hipótese em `premissa` e reflita isso na nota (ex.: dado inexistente ⇒ viabilidade menor). Inclua deliberadamente ao menos uma oportunidade fraca quando fizer sentido, para exercitar o quadrante *evitar · vaidade*.
7. Ao final, monte o `roadmap`: a ordem recomendada de execução (ids das oportunidades), começando pelos *ganho rápido*.

### Regra do quadrante (determinística)
Considere **alto = nota 4 ou 5** e **baixo = nota 1, 2 ou 3**.
- `valor` alto **e** `viabilidade` alta → `ganho_rapido`
- `valor` alto **e** `viabilidade` baixa → `aposta_estrategica`
- `valor` baixo **e** `viabilidade` alta → `incremental`
- `valor` baixo **e** `viabilidade` baixa → `evitar_vaidade`

### Dicionário de campos e valores permitidos
- `projeto`: `nome`, `descricao` (resumo em 1–2 frases), `setor`, `porte` (`pequeno` | `medio` | `grande`).
- `areas[]`:
  - `area` — nome da área de negócio.
  - `contexto` — bloco **01**: objetivos, KPIs e processos-chave da área.
  - `objetivo_estrategico` — o que a área precisa entregar.
  - `oportunidades[]`:
    - `id` — slug estável `"{area-slug}-NN"` (ex.: `"atendimento-01"`).
    - `dor` — bloco **02**: o problema real (a dor, não a solução).
    - `oportunidade` — bloco **03**: em uma frase, o que a IA faria e qual dor ataca.
    - `tipo[]` — bloco **03**, um ou mais de: `automacao` | `classificacao_previsao` | `extracao_busca` | `geracao` | `copiloto` | `agente`.
    - `dados` — bloco **04**: `descricao` (que dados alimentam) e `disponibilidade` (`alta` | `media` | `baixa`).
    - `valor` — bloco **05**: `direto`, `indireto`, `metrica` (métrica de sucesso com linha de base quando possível).
    - `custo` — bloco **06**: `capex` (`baixo` | `medio` | `alto`), `opex` (`baixo` | `medio` | `alto`), `integracao` (`baixa` | `media` | `alta`), `mudanca` (esforço de processo/pessoas).
    - `riscos` — bloco **07**: `descricao`, `regulatorio[]` (ex.: `["LGPD"]`, `[]` se nenhum), `human_in_the_loop` (`nenhum` | `sugerir` | `aprovar` | `supervisionar`).
    - `decisao` — bloco **08**: `valor` (1–5), `viabilidade` (1–5), `quadrante` (derivado pela regra), `proximo_passo`.
    - `premissa` — hipótese assumida por falta de informação (string vazia se não houver).
- `roadmap[]` — objetos `{ "id", "justificativa" }` na ordem recomendada de execução.

### Formato de saída (obrigatório)
Responda **somente** com o objeto JSON, começando em `{` e terminando em `}`. **Sem** cercas de código, **sem** comentários e **sem** qualquer texto antes ou depois. Use exatamente estas chaves. Mantenha `schema` e `versao` como no exemplo.

### Exemplo de saída (estrutura e estilo esperados)
{
  "schema": "aegis.canvas-oportunidades",
  "versao": "1",
  "status": "rascunho",
  "gerado_por": "claude",
  "projeto": {
    "nome": "Rede Aurora",
    "descricao": "Rede varejista de médio porte, ~40 lojas no Nordeste e e-commerce em crescimento.",
    "setor": "varejo",
    "porte": "medio"
  },
  "areas": [
    {
      "area": "Atendimento ao Cliente (SAC)",
      "contexto": "~12 mil contatos/mes (WhatsApp, telefone, e-mail) com 18 atendentes. KPIs: tempo de resposta e CSAT.",
      "objetivo_estrategico": "Reduzir tempo de resposta e elevar CSAT sem ampliar a equipe.",
      "oportunidades": [
        {
          "id": "atendimento-01",
          "dor": "~60% dos contatos sao duvidas repetidas (status de pedido, troca, horario); o repetitivo consome a equipe e o caso complexo espera na fila.",
          "oportunidade": "Copiloto que sugere respostas ao atendente e resolve automaticamente as intencoes repetidas de status e troca.",
          "tipo": ["copiloto", "automacao"],
          "dados": {
            "descricao": "2 anos de tickets no CRM + base de FAQ; integracao com ERP de pedidos via API ja existe; categorizacao inconsistente.",
            "disponibilidade": "media"
          },
          "valor": {
            "direto": "Liberar ~40% do tempo gasto em contatos repetidos.",
            "indireto": "Menos erro humano e fila menor em picos.",
            "metrica": "Tempo de resposta -30% e CSAT +5 pontos."
          },
          "custo": {
            "capex": "baixo",
            "opex": "medio",
            "integracao": "media",
            "mudanca": "Treinar 18 atendentes e ajustar o script de atendimento."
          },
          "riscos": {
            "descricao": "Risco de resposta errada em troca/reembolso; alucinacao em politica de troca.",
            "regulatorio": ["LGPD"],
            "human_in_the_loop": "aprovar"
          },
          "decisao": {
            "valor": 4,
            "viabilidade": 4,
            "quadrante": "ganho_rapido",
            "proximo_passo": "PoC de 4 semanas com as 5 intencoes mais frequentes; atendente aprova antes de enviar."
          },
          "premissa": ""
        }
      ]
    },
    {
      "area": "Financeiro",
      "contexto": "Controladoria com rotinas manuais de conciliacao e relatorios gerenciais.",
      "objetivo_estrategico": "Fechar o mes mais rapido e com menos erro.",
      "oportunidades": [
        {
          "id": "financeiro-01",
          "dor": "Diretoria quer 'um dashboard com IA generativa' sem uma dor operacional clara por tras.",
          "oportunidade": "Assistente que resume indicadores em linguagem natural sobre os relatorios existentes.",
          "tipo": ["geracao"],
          "dados": {
            "descricao": "Relatorios ja existem em BI; o ganho incremental sobre eles e pequeno.",
            "disponibilidade": "alta"
          },
          "valor": {
            "direto": "Economia marginal de tempo de leitura de relatorio.",
            "indireto": "Percepcao de modernidade.",
            "metrica": "Sem metrica de negocio clara."
          },
          "custo": {
            "capex": "medio",
            "opex": "medio",
            "integracao": "media",
            "mudanca": "Baixa adocao esperada sem dor real."
          },
          "riscos": {
            "descricao": "Risco de numeros resumidos incorretamente; baixa confianca do usuario.",
            "regulatorio": [],
            "human_in_the_loop": "supervisionar"
          },
          "decisao": {
            "valor": 2,
            "viabilidade": 2,
            "quadrante": "evitar_vaidade",
            "proximo_passo": "Nao priorizar; revisitar apenas se surgir uma dor concreta."
          },
          "premissa": "Assumido que os relatorios de BI atuais ja atendem bem a diretoria."
        }
      ]
    }
  ],
  "roadmap": [
    { "id": "atendimento-01", "justificativa": "Ganho rapido: alto valor e alta viabilidade; comecar por aqui." },
    { "id": "financeiro-01", "justificativa": "Evitar por ora: sem dor real nem metrica de negocio." }
  ]
}

### DESCRIÇÃO DO PROJETO
{{cole aqui a descrição geral do projeto/empresa — setor, porte, o que faz, principais processos e dores conhecidas. Quanto mais contexto, melhor o rascunho.}}

## (fim do prompt)

---

### Notas de uso
- O JSON gerado é um **rascunho** — revise as notas de Valor/Viabilidade com o time; elas existem para forçar consenso, não para serem exatas.
- A regra do quadrante é determinística, então o campo `quadrante` sempre bate com as notas. Se você mudar uma nota na plataforma, recalcule o quadrante pela mesma regra (alto = 4–5).
- Combina com o prompt equivalente da **SWOT de IA** (`aegis.swot-ia`): rode a SWOT para a leitura macro e o canvas para as oportunidades por área.
