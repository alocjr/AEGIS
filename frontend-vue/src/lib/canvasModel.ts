/** Modelo do canvas de oportunidades (AR-02). */

export type EvalField = 'valor' | 'dados' | 'custo' | 'riscos'

export type EvalHelp = {
  field: EvalField
  num: string
  title: string
  hint: string
  tagline: string
  answers: string
  pulls: string
  questions: string[]
  examples: string[]
  alert: string
}

/** Banda de Avaliação — repertório de partida (perguntas + exemplos). */
export const EVAL_CELLS: EvalHelp[] = [
  {
    field: 'valor',
    num: '04',
    title: 'Valor esperado',
    hint: 'Ganho direto (tempo/custo/receita) + indireto (qualidade/risco). Como medir?',
    tagline: 'o porquê',
    answers: 'Que ganho concreto essa oportunidade traz, e como vamos medir se deu certo?',
    pulls: 'Puxa a nota de Valor no bloco 08.',
    questions: [
      'Qual o ganho direto: tempo economizado, custo reduzido, receita gerada, capacidade liberada?',
      'Qual o ganho indireto: qualidade, redução de risco, experiência do cliente, retenção?',
      'Quem sente o ganho — a área, o cliente, a empresa toda?',
      'Qual a métrica de sucesso e a linha de base atual (de X para Y)?',
      'Em quanto tempo o valor aparece — semanas, um trimestre, um ano?',
    ],
    examples: [
      'Reduzir ~40% do tempo gasto em contatos repetidos; liberar a equipe para o caso complexo.',
      'Meta: tempo de resposta de 8 h → 5 h (−30%) e CSAT de 72 → 77.',
      'Aumentar conversão do e-commerce em 3–5 p.p. com recomendação personalizada.',
      'Cortar 15 h/semana de trabalho manual de conciliação no Financeiro.',
      'Reduzir prazo de revisão de contratos de 5 dias → 2 dias no Jurídico.',
      'Ganho indireto: menos erro humano em cálculo de reembolso (redução de risco).',
      'Ganho de capacidade: atender 30% mais pedidos sem aumentar o time.',
      'Métrica de sucesso definida: "% de contatos resolvidos sem intervenção humana".',
    ],
    alert:
      'Se ninguém consegue nomear a métrica nem a linha de base, o “valor” ainda é entusiasmo — não dá para pontuar o bloco 08 com honestidade.',
  },
  {
    field: 'dados',
    num: '05',
    title: 'Dados & insumos',
    hint: 'Combustível: volume, qualidade, acesso, formato. Sem dado, não sai do papel.',
    tagline: 'o veto',
    answers: 'Existe dado disponível, com qualidade e acesso, para alimentar essa oportunidade? Sem isso, ela não sai do papel.',
    pulls: 'Puxa a nota de Viabilidade no bloco 08.',
    questions: [
      'Que dado a IA precisa consumir para funcionar? Ele existe hoje?',
      'Onde está — sistema, planilha, e-mail, cabeça das pessoas? É acessível via API/export?',
      'Qual o volume e o histórico disponível (meses/anos, nº de registros)?',
      'Qual a qualidade: está estruturado, rotulado, atualizado, consistente?',
      'Há restrição de acesso (base de terceiros, dado pessoal, contrato)?',
    ],
    examples: [
      'Histórico de ~2 anos de tickets no CRM; categorização inconsistente (qualidade média).',
      'Base de FAQ e políticas em documentos soltos; precisa ser consolidada antes de usar.',
      'Dados de vendas por loja no ERP, com integração via API já disponível.',
      'Estoque fragmentado entre 3 sistemas que não conversam (bloqueador de viabilidade).',
      'Contratos em PDF escaneado (imagem, não texto) — exige OCR antes de qualquer extração.',
      'Dados de clientes sujeitos à LGPD; acesso exige base legal e anonimização.',
      'Volume alto e diário (bom para aprendizado); porém sem rótulo de “resolvido/não resolvido”.',
      'O dado existe só no conhecimento tácito da equipe — não capturado em lugar nenhum.',
    ],
    alert:
      'Se a resposta for “teríamos que começar a coletar do zero”, a viabilidade cai e a oportunidade provavelmente é uma aposta estratégica, não um ganho rápido.',
  },
  {
    field: 'custo',
    num: '06',
    title: 'Custo & complexidade',
    hint: 'CapEx (construir) × OpEx (operar: inferência/tokens + manutenção) + integração.',
    tagline: 'o preço real',
    answers: 'Quanto custa construir e, principalmente, operar e integrar isso ao dia a dia?',
    pulls: 'Puxa as notas de Valor e de Viabilidade no bloco 08.',
    questions: [
      'CapEx (construir): desenvolvimento, configuração, integração inicial, curadoria de dados.',
      'OpEx (operar): custo de inferência/tokens no volume real, licenças, manutenção, monitoramento.',
      'Qual a complexidade de integração com os sistemas atuais?',
      'Qual a mudança de processo e de pessoas necessária (o 70% da regra 10-20-70)?',
      'É construir do zero, usar plataforma existente ou contratar pronto?',
    ],
    examples: [
      'CapEx baixo: usa a plataforma de atendimento que já temos; só configuração.',
      'OpEx de inferência moderado, mas sensível ao volume (alto nº de mensagens/mês).',
      'Integração média: já existe API do ERP; falta mapear os campos.',
      'Integração alta: exigiria conectar 3 sistemas legados — principal fonte de esforço.',
      'Custo humano real: treinar 18 atendentes e mudar o script de atendimento.',
      'Manutenção contínua: alguém precisa revisar respostas e reajustar mensalmente.',
      'Curadoria de dados como custo escondido: limpar e rotular a base antes de começar.',
      'Opção pronta de mercado reduz CapEx, mas cria OpEx recorrente de licença.',
    ],
    alert:
      'Se o time só falou de tecnologia e não citou pessoas/processo, o custo está subestimado — 70% do esforço mora justamente aí.',
  },
  {
    field: 'riscos',
    num: '07',
    title: 'Riscos & governança',
    hint: 'LGPD e regras do setor, alucinação, dependência. Que supervisão humana é obrigatória?',
    tagline: 'os limites',
    answers: 'O que pode dar errado e que supervisão é obrigatória para operar com segurança?',
    pulls: 'Puxa a nota de Viabilidade no bloco 08.',
    questions: [
      'Regulatório: LGPD, regras do setor (saúde, financeiro, jurídico), retenção de dados.',
      'Erro do modelo: o que acontece se a IA errar? O erro é reversível ou caro?',
      'Alucinação: a tarefa tolera resposta inventada? Onde isso seria perigoso?',
      'Dependência: ficamos reféns de um fornecedor, modelo ou dado externo?',
      'Autonomia: qual o nível de human-in-the-loop obrigatório — sugerir, aprovar ou agir sozinho?',
    ],
    examples: [
      'LGPD: dados pessoais de clientes → base legal, minimização e anonimização.',
      'Ação financeira (troca/reembolso) exige aprovação humana antes de executar.',
      'Alucinação inaceitável em política de troca → respostas restritas à base oficial.',
      'Setor regulado: no jurídico, toda peça gerada passa por revisão de advogado.',
      'Risco reputacional se o cliente perceber que falou com um bot sem aviso.',
      'Dependência de um único fornecedor de modelo → prever plano B / portabilidade.',
      'Nível de autonomia definido: copiloto sugere, humano aprova e envia (fase 1).',
      'Viés: recomendação de crédito/preço precisa de auditoria para evitar discriminação.',
    ],
    alert:
      'Se a oportunidade só é viável com a IA agindo sozinha em algo irreversível, o risco derruba a viabilidade — repense o escopo ou adie.',
  },
]

