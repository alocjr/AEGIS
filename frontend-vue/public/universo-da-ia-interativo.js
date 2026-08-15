const TECH = {
  // ===== CIÊNCIA DE DADOS =====
  "estatistica": {group:"Ciência de Dados", name:"Estatística", era:"Base desde o século XVIII", status:"ativa", statusLabel:"Fundamento sempre usado",
    desc:"Base matemática para inferência, testes de hipótese e intervalos de confiança que sustentam qualquer modelo de IA — sem estatística não há como saber se um resultado é real ou coincidência.",
    uses:["Validação de experimentos A/B","Controle de qualidade industrial","Definição de KPIs e métricas de negócio"]},
  "visualizacao-dados": {group:"Ciência de Dados", name:"Visualização de Dados", era:"Consolidada desde os anos 1980", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Técnicas gráficas — dashboards, gráficos, mapas de calor — que tornam dados e resultados de modelos compreensíveis para quem decide.",
    uses:["Dashboards executivos","Exploração de dados (EDA) antes de treinar modelos","Comunicação de resultados de ML para não técnicos"]},
  "armazenamento-dados": {group:"Ciência de Dados", name:"Armazenamento de Dados", era:"Em evolução constante", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Bancos relacionais, NoSQL, data lakes e data warehouses que guardam os dados usados para treinar e operar modelos de IA.",
    uses:["MongoDB / Postgres para aplicações","Snowflake / BigQuery para analytics","Data lakes para treino de LLMs"]},
  "design-experimentos": {group:"Ciência de Dados", name:"Design de Experimentos", era:"Formalizado nos anos 1920 (Fisher)", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Metodologia estatística para planejar testes controlados que isolam o efeito real de uma mudança, evitando conclusões enganosas.",
    uses:["Testes A/B e multivariados de produto","Otimização de prompts de LLMs","Comparação controlada entre modelos em produção"]},
  "engenharia-dados": {group:"Ciência de Dados", name:"Engenharia de Dados (ETL)", era:"Essencial desde sempre, reinventada com big data", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Pipelines de extração, transformação e carga que preparam dados brutos para uso em modelos e análises.",
    uses:["Pipelines de treino de modelos","Integração de sistemas legados","Feature stores para ML em produção"]},
  "big-data": {group:"Ciência de Dados", name:"Big Data & Computação Distribuída", era:"Auge 2010–2018", status:"nicho", statusLabel:"Uso especializado",
    desc:"Frameworks como Spark e Hadoop para processar volumes de dados que não cabem em uma única máquina. Parte do protagonismo migrou para data warehouses em nuvem.",
    uses:["Pré-processamento de datasets de treino de LLMs","Processamento de logs em escala","Análise de cliques em e-commerce"]},
  "qualidade-governanca": {group:"Ciência de Dados", name:"Qualidade & Governança de Dados", era:"Em forte expansão desde 2020", status:"ativa", statusLabel:"Muito usada, crescendo",
    desc:"Processos e ferramentas para garantir que os dados usados por modelos são precisos, completos e rastreáveis.",
    uses:["Catálogos de dados corporativos","Linhagem de dados (data lineage)","Compliance com LGPD e regulação setorial"]},

  // ===== PARADIGMA SIMBÓLICO =====
  "sistemas-especialistas": {group:"Paradigma Simbólico", name:"Sistemas Especialistas", era:"Auge nos anos 1970–1990", status:"nicho", statusLabel:"Uso especializado",
    desc:"Sistemas baseados em regras 'se-então' escritas por especialistas humanos para simular decisões em domínios específicos, como o pioneiro MYCIN em diagnóstico médico.",
    uses:["Motores de regras em crédito e compliance","Triagem médica básica em protocolos fechados","Configuradores de produto complexo"]},
  "ontologias": {group:"Paradigma Simbólico", name:"Ontologias & Grafos de Conhecimento", era:"Anos 1990 → ressurgindo agora", status:"ativa", statusLabel:"Ressurgindo com força",
    desc:"Estruturas formais que organizam conceitos de um domínio e suas relações, permitindo que máquinas 'entendam' significado, não só palavras.",
    uses:["Google Knowledge Graph","Integração de dados em saúde (SNOMED CT)","GraphRAG — combinar LLMs com grafos de conhecimento"]},
  "logica-programacao": {group:"Paradigma Simbólico", name:"Lógica & Programação Lógica", era:"Prolog, anos 1970", status:"historica", statusLabel:"Majoritariamente histórica",
    desc:"Programação declarativa baseada em lógica formal, onde o programa descreve fatos e regras e o sistema deriva conclusões automaticamente.",
    uses:["Sistemas de verificação formal","Planejadores de IA clássica","Ensino de lógica computacional"]},
  "busca-heuristica": {group:"Paradigma Simbólico", name:"Busca Heurística", era:"1950s → hoje", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Algoritmos que exploram espaços de estados usando heurísticas para encontrar soluções ótimas ou quase ótimas (A*, minimax, Monte Carlo Tree Search).",
    uses:["Motores de xadrez, como o histórico Deep Blue","GPS e roteamento de mapas","Parte do motor de busca por trás do AlphaGo"]},
  "planejamento-automatizado": {group:"Paradigma Simbólico", name:"Planejamento Automatizado", era:"Anos 1970 (STRIPS) → hoje", status:"nicho", statusLabel:"Uso especializado",
    desc:"Técnicas que geram sequências de ações para atingir um objetivo a partir de um estado inicial conhecido.",
    uses:["Planejamento de missões robóticas e espaciais (NASA)","Logística industrial complexa","Agentes de IA que decompõem tarefas em passos"]},
  "raciocinio-casos": {group:"Paradigma Simbólico", name:"Raciocínio Baseado em Casos (CBR)", era:"Anos 1980–1990", status:"historica", statusLabel:"Majoritariamente histórica",
    desc:"Resolve novos problemas recuperando e adaptando soluções de casos passados semelhantes, em vez de partir de regras gerais.",
    uses:["Help desks técnicos legados","Apoio à decisão jurídica por jurisprudência","Diagnóstico por analogia em engenharia"]},
  "redes-semanticas": {group:"Paradigma Simbólico", name:"Redes Semânticas & Frames", era:"Anos 1970–1980", status:"historica", statusLabel:"Majoritariamente histórica",
    desc:"Representam conhecimento como grafos de conceitos conectados por relações rotuladas; frames organizam atributos típicos de um conceito.",
    uses:["Precursoras diretas dos grafos de conhecimento modernos","Processamento de linguagem natural simbólico clássico"]},

  // ===== BIO-INSPIRADAS =====
  "comp-evolucionaria": {group:"Bio-inspiradas", name:"Computação Evolucionária", era:"Anos 1970 → nicho ativo", status:"nicho", statusLabel:"Uso especializado",
    desc:"Algoritmos que simulam seleção natural — mutação, cruzamento, seleção — para evoluir soluções a problemas de otimização.",
    uses:["Design de antenas da NASA","Otimização de portfólios financeiros","Tuning de hiperparâmetros de redes neurais"]},
  "enxames": {group:"Bio-inspiradas", name:"Inteligência de Enxames", era:"Anos 1990 → nicho ativo", status:"nicho", statusLabel:"Uso especializado",
    desc:"Inspirados no comportamento coletivo de formigas e pássaros (ACO, PSO), resolvem problemas de otimização de forma distribuída.",
    uses:["Roteamento de veículos e logística","Otimização de redes de telecomunicações"]},
  "sist-imunologicos": {group:"Bio-inspiradas", name:"Sistemas Imunológicos Artificiais", era:"Anos 1990–2000", status:"historica", statusLabel:"Majoritariamente histórica",
    desc:"Algoritmos inspirados no sistema imunológico biológico para detecção de anomalias e otimização.",
    uses:["Detecção de intrusão em segurança de redes (legado)","Detecção de fraude em sistemas antigos"]},
  "automatos-celulares": {group:"Bio-inspiradas", name:"Autômatos Celulares", era:"1940s (von Neumann) → nicho", status:"nicho", statusLabel:"Uso especializado",
    desc:"Modelos computacionais simples — grades de células com regras locais — que geram comportamento complexo emergente, como o Jogo da Vida de Conway.",
    uses:["Simulação de tráfego urbano","Modelagem de propagação de epidemias","Geração procedural em jogos"]},

  // ===== OUTRAS FAMÍLIAS =====
  "logica-fuzzy": {group:"Outras Famílias", name:"Lógica Fuzzy", era:"1965 (Zadeh) → hoje", status:"ativa", statusLabel:"Muito usada, embarcada",
    desc:"Permite raciocínio com graus de verdade entre 0 e 1, em vez de verdadeiro/falso puro, lidando bem com incerteza e imprecisão da linguagem natural.",
    uses:["Controle de ar-condicionado e câmbio automático","Sistemas de controle industrial"]},
  "otimizacao-metaheuristica": {group:"Outras Famílias", name:"Otimização Metaheurística", era:"Anos 1980 → hoje", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Estratégias gerais (Simulated Annealing, Busca Tabu, Hill Climbing) para encontrar boas soluções em problemas grandes demais para busca exaustiva.",
    uses:["Roteirização de entregas","Escalonamento de produção industrial"]},
  "agentes-multiagente": {group:"Outras Famílias", name:"Agentes & Sistemas Multiagente", era:"Anos 1980 → base da IA agêntica atual", status:"ativa", statusLabel:"Muito usada, base conceitual atual",
    desc:"Sistemas onde múltiplos agentes autônomos interagem, cooperam ou competem para atingir objetivos (arquitetura BDI: crenças, desejos, intenções).",
    uses:["Simulação de mercados financeiros","Leilões automatizados","Base conceitual dos agentes de IA modernos"]},

  // ===== PROBABILÍSTICO =====
  "redes-bayesianas": {group:"Raciocínio Probabilístico", name:"Redes Bayesianas & Naive Bayes", era:"Anos 1980 → hoje", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Modelos gráficos que representam relações de dependência probabilística entre variáveis, permitindo inferência sob incerteza.",
    uses:["Diagnóstico médico probabilístico","Filtros de spam clássicos","Sistemas de recomendação simples"]},
  "hmm-mdp": {group:"Raciocínio Probabilístico", name:"HMM · MDP · Modelos Gráficos", era:"Anos 1970–1990", status:"nicho", statusLabel:"Uso especializado",
    desc:"Modelos que descrevem sistemas com estados ocultos que evoluem no tempo (HMM) ou processos de decisão sequencial (MDP) — base teórica do aprendizado por reforço.",
    uses:["Reconhecimento de fala clássico","Robótica de navegação","Precificação dinâmica"]},
  "inferencia-causal": {group:"Raciocínio Probabilístico", name:"Inferência Causal", era:"Framework moderno de Judea Pearl", status:"fronteira", statusLabel:"Fronteira de pesquisa",
    desc:"Framework para distinguir correlação de causalidade e responder perguntas contrafactuais — 'o que teria acontecido se...'.",
    uses:["Avaliação de políticas públicas","Medicina baseada em evidência","Growth e experimentação em produtos digitais"]},

  // ===== NEURO-SIMBÓLICA =====
  "neuro-simbolica": {group:"Fronteira", name:"IA Neuro-simbólica", era:"Fronteira de pesquisa ativa (2020s)", status:"fronteira", statusLabel:"Fronteira de pesquisa",
    desc:"Combina redes neurais, que aprendem padrões, com representação simbólica, que raciocina com regras — busca o melhor dos dois mundos: aprendizado com explicabilidade verificável.",
    uses:["AlphaGeometry — resolve problemas de geometria olímpica","LLMs aumentados com grafos de conhecimento (GraphRAG)","Verificação formal de código gerado por IA"]},

  // ===== ML SUPERVISIONADO =====
  "regressao": {group:"Machine Learning", name:"Regressão Linear & Logística", era:"Século XIX/XX, base do ML", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Modelos que preveem um valor numérico (linear) ou uma classe (logística) a partir de uma combinação de variáveis de entrada.",
    uses:["Previsão de vendas","Score de crédito","Previsão de churn de clientes"]},
  "arvores-rf": {group:"Machine Learning", name:"Árvores de Decisão & Random Forest", era:"Anos 1990 → hoje", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Árvores de decisão dividem dados por perguntas sucessivas; Random Forest combina muitas árvores para maior precisão e estabilidade.",
    uses:["Detecção de fraude bancária","Modelos de risco de crédito","Triagem médica assistida"]},
  "boosting": {group:"Machine Learning", name:"Boosting (XGBoost, LightGBM)", era:"2010s → padrão-ouro atual", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Combina modelos fracos sequencialmente, cada um corrigindo os erros do anterior — hoje é o padrão-ouro para dados tabulares estruturados.",
    uses:["Competições de dados (Kaggle)","Scoring de crédito em produção","Precificação de seguros"]},
  "svm-knn-nb": {group:"Machine Learning", name:"SVM · KNN · Naive Bayes", era:"Anos 1990–2000, hoje complementares", status:"nicho", statusLabel:"Uso especializado",
    desc:"SVM encontra a fronteira ótima entre classes; KNN classifica por vizinhança; Naive Bayes usa probabilidade condicional simples e rápida.",
    uses:["Classificação de texto em datasets pequenos","Reconhecimento de padrões com poucos dados","Sistemas de recomendação básicos"]},

  // ===== ML NÃO SUPERVISIONADO =====
  "clusterizacao": {group:"Machine Learning", name:"Clusterização (K-means, DBSCAN)", era:"Anos 1960 → hoje", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Agrupa dados semelhantes entre si sem usar rótulos prévios, revelando estrutura escondida nos dados.",
    uses:["Segmentação de clientes","Agrupamento de documentos e conteúdo","Detecção de anomalias operacionais"]},
  "pca-tsne-umap": {group:"Machine Learning", name:"PCA · t-SNE · UMAP", era:"PCA (1901) a UMAP (2018)", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Técnicas de redução de dimensionalidade que preservam a estrutura dos dados para visualização ou como pré-processamento.",
    uses:["Visualização de embeddings de LLMs","Compressão de features antes do treino","Remoção de ruído em datasets"]},
  "associacao": {group:"Machine Learning", name:"Regras de Associação (Apriori)", era:"Anos 1990", status:"nicho", statusLabel:"Uso especializado",
    desc:"Descobre regras de associação entre itens frequentemente relacionados — o clássico 'quem compra X também compra Y'.",
    uses:["Recomendação de produtos em e-commerce","Análise de cesta de compras no varejo"]},

  // ===== ML REFORÇO =====
  "q-learning-dqn": {group:"Machine Learning", name:"Q-Learning & Deep Q-Networks", era:"1989 (Q-Learning) → 2013 (DQN)", status:"nicho", statusLabel:"Uso especializado",
    desc:"Aprende uma política de ação por tentativa e erro, maximizando recompensas acumuladas ao longo do tempo.",
    uses:["Controle de robôs","Otimização de refrigeração em datacenters (caso Google/DeepMind)","Jogos e simulações"]},
  "alphago": {group:"Machine Learning", name:"AlphaGo & AlphaZero", era:"Marco de 2016", status:"historica", statusLabel:"Marco histórico, técnica evoluiu",
    desc:"Combinou aprendizado por reforço e busca em árvore para vencer o campeão mundial de Go, provando que RL supera intuição humana em domínios complexos.",
    uses:["Base conceitual do AlphaFold (descoberta de proteínas)","AlphaTensor (otimização de algoritmos)","Motores de jogos estratégicos modernos"]},
  "rlhf": {group:"Machine Learning", name:"RLHF — Reforço com Feedback Humano", era:"Popularizado em 2022 com o ChatGPT", status:"ativa", statusLabel:"Crítica hoje",
    desc:"Ajusta modelos de linguagem usando preferências humanas como sinal de recompensa — foi a técnica que tornou o ChatGPT utilizável e 'alinhado'.",
    uses:["Fine-tuning de todos os grandes LLMs (GPT, Claude, Gemini)","Moderação e filtragem de conteúdo","Alinhamento de comportamento e tom da IA"]},

  // ===== ML OUTROS REGIMES =====
  "series-temporais": {group:"Machine Learning", name:"Séries Temporais", era:"Clássica, reforçada com deep learning", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Modelos especializados em prever valores futuros a partir de padrões históricos sequenciais (ARIMA, Prophet, modelos neurais temporais).",
    uses:["Previsão de demanda e estoque","Previsão financeira","Previsão climática"]},
  "self-superv-federado": {group:"Machine Learning", name:"Self-supervised & Aprendizado Federado", era:"2018 → em forte crescimento", status:"ativa", statusLabel:"Muito usada, crescendo",
    desc:"Aprendizado auto-supervisionado gera seus próprios rótulos a partir dos dados (base do pré-treino de LLMs); federado treina em dados distribuídos sem centralizá-los.",
    uses:["Pré-treino de todos os grandes LLMs","Teclados preditivos sem enviar dados do usuário","Modelos de saúde multi-hospitalares"]},
  "automl": {group:"Machine Learning", name:"AutoML", era:"2015 → consolidado", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Automatiza a seleção de modelo, features e hiperparâmetros, reduzindo a dependência de um especialista para tarefas de ML padrão.",
    uses:["Google Vertex AI AutoML","DataRobot","Prototipagem rápida em empresas sem equipe de ML madura"]},

  // ===== REDES NEURAIS =====
  "perceptron": {group:"Redes Neurais", name:"Perceptron", era:"1958 (Frank Rosenblatt)", status:"historica", statusLabel:"Majoritariamente histórica",
    desc:"O primeiro modelo de neurônio artificial, capaz de aprender fronteiras lineares simples. Sua limitação (não resolve XOR) causou o primeiro 'inverno da IA'.",
    uses:["Hoje é puramente pedagógico","Bloco de construção conceitual de toda rede neural moderna"]},
  "mlp-backprop": {group:"Redes Neurais", name:"Perceptron Multicamadas & Backpropagation", era:"1986 (Rumelhart, Hinton, Williams)", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Permitiu treinar redes com camadas ocultas, resolvendo problemas não lineares — é a arquitetura básica dentro de praticamente todo modelo de deep learning atual.",
    uses:["Camadas densas em qualquer rede neural moderna","Classificadores simples em produção"]},
  "som": {group:"Redes Neurais", name:"Mapas Auto-Organizáveis (SOM)", era:"1982 (Teuvo Kohonen)", status:"historica", statusLabel:"Majoritariamente histórica",
    desc:"Redes que se auto-organizam para mapear dados de alta dimensão em um espaço 2D, preservando relações de similaridade.",
    uses:["Visualização de dados complexos","Segmentação de mercado (uso legado)","Detecção de padrões em genômica"]},
  "hopfield-boltzmann": {group:"Redes Neurais", name:"Redes de Hopfield & Máquinas de Boltzmann", era:"1982–1985", status:"historica", statusLabel:"Majoritariamente histórica",
    desc:"Redes recorrentes que funcionam como memórias associativas (Hopfield) ou aprendem distribuições de probabilidade (Boltzmann) — precursoras conceituais do deep learning moderno.",
    uses:["Hoje majoritariamente históricas","Inspiraram autoencoders e modelos de energia usados em difusão"]},

  // ===== DEEP LEARNING =====
  "visao-cnn": {group:"Deep Learning", name:"Visão Computacional (CNN)", era:"2012 (AlexNet) → hoje", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Redes Convolucionais aprendem a reconhecer padrões visuais hierárquicos — bordas, formas, objetos — através de filtros aplicados à imagem.",
    uses:["Diagnóstico por imagem médica (raio-x, ressonância)","Inspeção de qualidade industrial","Reconhecimento facial e biometria"]},
  "fala-audicao-rnn": {group:"Deep Learning", name:"Fala & Audição (RNN, LSTM)", era:"Anos 1990–2010, hoje superadas", status:"nicho", statusLabel:"Uso especializado",
    desc:"Redes recorrentes processam sequências temporais — foram a base clássica do reconhecimento de fala e tradução antes dos Transformers.",
    uses:["Assistentes de voz de primeira geração","Análise de séries temporais e sinais de sensores"]},
  "sinais-autoencoders": {group:"Deep Learning", name:"Processamento de Sinais & Autoencoders", era:"Consolidada, em uso crescente", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Deep learning aplicado a sons, vibrações e sensores; autoencoders aprendem a comprimir e reconstruir dados, úteis para detectar anomalias.",
    uses:["Manutenção preditiva industrial (vibração de máquinas)","Compressão de imagem","Detecção de fraude por reconstrução anômala"]},
  "gnn": {group:"Deep Learning", name:"Redes Neurais de Grafos (GNN)", era:"2017 → em forte crescimento", status:"ativa", statusLabel:"Muito usada, crescendo",
    desc:"Aprendem representações de nós considerando suas conexões — essenciais para dados relacionais como redes sociais, moléculas e mapas.",
    uses:["Descoberta de fármacos (previsão de propriedades moleculares)","Detecção de fraude em redes de transações","Recomendação no Pinterest e Alibaba"]},
  "mod-difusao": {group:"Deep Learning", name:"Modelos de Difusão", era:"2020 → estado da arte", status:"ativa", statusLabel:"Estado da arte hoje",
    desc:"Aprendem a gerar dados revertendo gradualmente um processo de adição de ruído — a arquitetura por trás da atual geração de imagens por IA.",
    uses:["Midjourney, Stable Diffusion, DALL-E","Geração de vídeo (Sora, Veo)"]},
  "nerf-3d": {group:"Deep Learning", name:"NeRF & Gaussian Splatting", era:"2020 → fronteira ativa", status:"fronteira", statusLabel:"Fronteira de pesquisa",
    desc:"Reconstroem cenas 3D fotorrealistas a partir de fotos 2D usando redes neurais; Gaussian Splatting é uma técnica mais recente e rápida para o mesmo fim.",
    uses:["Captura de cenas 3D para VR e games","Efeitos visuais em cinema","Digitalização de patrimônio histórico"]},

  // ===== IA GENERATIVA =====
  "gan-vae": {group:"IA Generativa", name:"GAN & VAE", era:"2014 (GAN) / 2013 (VAE) → superadas em imagem", status:"nicho", statusLabel:"Uso especializado",
    desc:"GANs usam dois modelos competindo entre si para gerar dados realistas; VAEs aprendem uma representação compacta e geram variações a partir dela.",
    uses:["Geração de rostos sintéticos para pesquisa","Síntese de dados quando há poucos dados reais","Primeiras gerações de deepfakes"]},
  "transformers": {group:"IA Generativa", name:"Transformers", era:"2017 — 'Attention Is All You Need'", status:"ativa", statusLabel:"Padrão-ouro atual",
    desc:"Arquitetura que processa sequências inteiras em paralelo usando 'atenção', em vez de passo a passo como as RNNs — é a base de todos os LLMs modernos.",
    uses:["Todos os grandes modelos de linguagem","Tradução automática e geração de código","Vision Transformers em visão computacional"]},
  "llms": {group:"IA Generativa", name:"LLMs — Grandes Modelos de Linguagem", era:"2018 → explosão desde 2022", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Transformers treinados em volumes massivos de texto para prever a próxima palavra, adquirindo capacidades emergentes de raciocínio, escrita e código.",
    uses:["Assistentes conversacionais (GPT, Claude, Gemini)","Geração e revisão de código","Análise e síntese de documentos longos"]},
  "geracao-multimidia": {group:"IA Generativa", name:"Geração de Imagem, Vídeo, Áudio e Código", era:"2022 → em expansão acelerada", status:"ativa", statusLabel:"Muito usada, crescendo",
    desc:"Modelos generativos especializados por modalidade — imagem, vídeo, voz e código — derivados de arquiteturas de difusão ou Transformers.",
    uses:["Produção de marketing e design (Midjourney)","Dublagem e clonagem de voz (ElevenLabs)","Prototipagem de software (Claude Code, Copilot)"]},

  // ===== IA AGÊNTICA =====
  "ia-agentica": {group:"Fronteira", name:"IA Agêntica", era:"2024 → evoluindo rapidamente", status:"fronteira", statusLabel:"Fronteira de pesquisa",
    desc:"LLMs que deixam de apenas responder e passam a agir de forma autônoma: decidem quais ferramentas usar, executam ações e observam resultados (ciclo ReAct), muitas vezes coordenando múltiplos agentes.",
    uses:["Agentes de codificação autônomos (Claude Code)","Automação de pesquisa e atendimento","Orquestração de fluxos de trabalho empresariais"]},

  // ===== APLICAÇÕES =====
  "app-visao": {group:"Aplicações", name:"Visão Computacional (aplicação)", era:"Consolidada", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Aplica deep learning — majoritariamente CNNs e Vision Transformers — para que máquinas 'enxerguem' e interpretem imagens e vídeos.",
    uses:["Inspeção de qualidade em fábricas","Diagnóstico por imagem médica","Veículos autônomos e biometria facial"]},
  "app-pln": {group:"Aplicações", name:"PLN — Processamento de Linguagem Natural", era:"Hoje dominado por LLMs", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Cobre todo o espectro de tarefas com texto — hoje majoritariamente resolvido por LLMs baseados em Transformers.",
    uses:["Chatbots e atendimento automatizado","Análise de sentimento","Extração de informação de contratos"]},
  "app-fala": {group:"Aplicações", name:"Fala (ASR & TTS, aplicação)", era:"Hoje baseada em Transformers e difusão", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Reconhecimento de fala (ASR) e síntese de voz (TTS), hoje majoritariamente baseados em Transformers e modelos de difusão de áudio.",
    uses:["Assistentes de voz","Transcrição automática de reuniões","Dublagem e clonagem de voz"]},
  "app-robotica": {group:"Aplicações", name:"Robótica & IA Incorporada (Embodied AI)", era:"Acelerando desde 2023 com LLMs multimodais", status:"fronteira", statusLabel:"Fronteira de pesquisa",
    desc:"Combina visão, controle e aprendizado por reforço para que sistemas físicos ajam de forma autônoma no mundo real.",
    uses:["Braços robóticos industriais","Robôs humanoides (Figure, Optimus)","Drones autônomos e cirurgia robótica assistida"]},
  "app-recomendacao": {group:"Aplicações", name:"Sistemas de Recomendação", era:"Consolidada, reforçada com deep learning", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Combina filtragem colaborativa, embeddings e deep learning para prever o que um usuário vai querer ver ou comprar.",
    uses:["Netflix e Spotify","Feed do Instagram e TikTok","Recomendação de produtos na Amazon"]},
  "app-veiculos": {group:"Aplicações", name:"Veículos Autônomos", era:"Operação comercial limitada desde 2023", status:"fronteira", statusLabel:"Fronteira de pesquisa",
    desc:"Combina visão computacional, sensores (LiDAR/radar), planejamento simbólico e aprendizado por reforço em um único sistema.",
    uses:["Waymo e Tesla FSD em operação comercial limitada","Caminhões autônomos de longa distância","Robôs de entrega urbana"]},

  // ===== SUPORTE =====
  "hardware": {group:"Suporte", name:"Hardware: GPU · TPU · NPU · Neuromórfica", era:"Em corrida acelerada desde 2012", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Chips especializados em processamento paralelo massivo, essenciais para treinar e rodar modelos de deep learning em tempo viável.",
    uses:["Treino de LLMs em clusters de GPU (NVIDIA H100/B200)","Inferência em dispositivos móveis via NPU","Datacenters dedicados a IA"]},
  "mlops-llmops": {group:"Suporte", name:"MLOps / LLMOps", era:"Consolidando-se desde 2019", status:"ativa", statusLabel:"Muito usada hoje",
    desc:"Práticas e ferramentas para versionar, testar, implantar e monitorar modelos de IA em produção de forma confiável e repetível.",
    uses:["Pipelines de CI/CD para modelos","Monitoramento de drift de dados","Avaliação contínua de qualidade de LLMs"]},
  "xai": {group:"Suporte", name:"IA Explicável (XAI)", era:"Exigência crescente desde 2018", status:"ativa", statusLabel:"Cada vez mais exigida por lei",
    desc:"Técnicas como SHAP e LIME tentam tornar as decisões de modelos complexos, especialmente deep learning, compreensíveis para humanos.",
    uses:["Justificar negativas de crédito exigidas por regulação","Auditoria de modelos de risco","Depuração de vieses em modelos de contratação"]},
  "seguranca-alinhamento": {group:"Suporte", name:"Segurança & Alinhamento (AI Safety)", era:"Área de pesquisa em rápida expansão", status:"fronteira", statusLabel:"Fronteira de pesquisa",
    desc:"Busca garantir que sistemas de IA cada vez mais capazes ajam de acordo com a intenção humana, evitando comportamentos indesejados ou perigosos.",
    uses:["Red-teaming de LLMs antes do lançamento","Constitutional AI (abordagem da Anthropic)","Pesquisa em interpretabilidade mecanicista"]},
  "etica-governanca": {group:"Suporte", name:"Ética, Governança & Regulação", era:"Em rápida expansão regulatória (2024–2026)", status:"ativa", statusLabel:"Muito usada, crescendo",
    desc:"Frameworks regulatórios e éticos que definem limites e responsabilidades para o desenvolvimento e uso de IA.",
    uses:["EU AI Act — classificação de risco por aplicação","PL 2338 no Brasil","Políticas internas de governança de IA em empresas"]}
};

// ===== LAYOUT: coordenadas de cada pill (id, geometria, texto, variante visual) =====
const PILLS = [
  // Ciência de Dados (satélites)
  {id:"estatistica", x:1658,y:300,w:200,h:44,rx:22,fs:13,label:"Estatística"},
  {id:"visualizacao-dados", x:1658,y:364,w:200,h:44,rx:22,fs:12,label:"Visualização de Dados"},
  {id:"armazenamento-dados", x:1658,y:428,w:200,h:44,rx:22,fs:12,label:"Armazenamento de Dados"},
  {id:"design-experimentos", x:1658,y:492,w:200,h:44,rx:22,fs:12,label:"Design de Experimentos"},
  {id:"engenharia-dados", x:1658,y:556,w:200,h:44,rx:22,fs:12,label:"Engenharia de Dados (ETL)"},
  {id:"big-data", x:1658,y:620,w:200,h:44,rx:22,fs:12,label:"Big Data & Distribuída"},
  {id:"qualidade-governanca", x:1658,y:684,w:200,h:44,rx:22,fs:12,label:"Qualidade & Governança"},

  // Paradigma Simbólico
  {id:"sistemas-especialistas", x:154,y:374,w:382,h:27,rx:13.5,fs:11,label:"Sistemas Especialistas · motores de regras"},
  {id:"ontologias", x:154,y:414,w:382,h:27,rx:13.5,fs:11,label:"Ontologias & Grafos de Conhecimento"},
  {id:"logica-programacao", x:154,y:454,w:382,h:27,rx:13.5,fs:11,label:"Lógica & Programação Lógica (Prolog)"},
  {id:"busca-heuristica", x:154,y:494,w:382,h:27,rx:13.5,fs:11,label:"Busca Heurística (A*, minimax, MCTS)"},
  {id:"planejamento-automatizado", x:154,y:534,w:382,h:27,rx:13.5,fs:11,label:"Planejamento Automatizado (STRIPS)"},
  {id:"raciocinio-casos", x:154,y:574,w:382,h:27,rx:13.5,fs:11,label:"Raciocínio Baseado em Casos (CBR)"},
  {id:"redes-semanticas", x:154,y:614,w:382,h:27,rx:13.5,fs:11,label:"Redes Semânticas & Frames · KRR"},

  // Bio-inspiradas
  {id:"comp-evolucionaria", x:154,y:758,w:182,h:25,rx:12.5,fs:10.5,label:"Comp. Evolucionária (AG·PG)"},
  {id:"enxames", x:154,y:796,w:182,h:25,rx:12.5,fs:10.5,label:"Enxames (ACO · PSO)"},
  {id:"sist-imunologicos", x:154,y:834,w:182,h:25,rx:12.5,fs:10.5,label:"Sist. Imunológicos Artif."},
  {id:"automatos-celulares", x:154,y:872,w:182,h:25,rx:12.5,fs:10.5,label:"Autômatos Celulares"},

  // Outras Famílias
  {id:"logica-fuzzy", x:404,y:761,w:182,h:26,rx:13,fs:11,label:"Lógica Fuzzy"},
  {id:"otimizacao-metaheuristica", x:404,y:803,w:182,h:26,rx:13,fs:10.5,label:"Otimização Metaheurística"},
  {id:"agentes-multiagente", x:404,y:845,w:182,h:26,rx:13,fs:11,label:"Agentes & Multiagente"},

  // Probabilístico (variante "stone")
  {id:"redes-bayesianas", x:654,y:823,w:212,h:26,rx:13,fs:10.5,label:"Redes Bayesianas · Naive Bayes",variant:"stone"},
  {id:"hmm-mdp", x:654,y:860,w:212,h:26,rx:13,fs:10.5,label:"HMM · MDP · Mod. Gráficos",variant:"stone"},
  {id:"inferencia-causal", x:654,y:897,w:212,h:26,rx:13,fs:10.5,label:"Inferência Causal (Pearl)",variant:"stone"},

  // ML Supervisionado
  {id:"regressao", x:1018,y:388,w:150,h:24,rx:12,fs:10,label:"Regressão Lin. & Log."},
  {id:"arvores-rf", x:990,y:426,w:170,h:24,rx:12,fs:10,label:"Árvores · Random Forest"},
  {id:"boosting", x:968,y:464,w:158,h:24,rx:12,fs:10,label:"Boosting (XGBoost)"},
  {id:"svm-knn-nb", x:953,y:502,w:148,h:24,rx:12,fs:9.5,label:"SVM · KNN · N. Bayes"},

  // ML Não supervisionado
  {id:"clusterizacao", x:939,y:566,w:128,h:24,rx:12,fs:9,label:"Clusterização (K-means)"},
  {id:"pca-tsne-umap", x:937,y:602,w:126,h:24,rx:12,fs:9.5,label:"PCA · t-SNE · UMAP"},
  {id:"associacao", x:939,y:638,w:122,h:24,rx:12,fs:9.5,label:"Associação (Apriori)"},

  // ML Reforço
  {id:"q-learning-dqn", x:952,y:698,w:120,h:24,rx:12,fs:9.5,label:"Q-Learning · DQN"},
  {id:"alphago", x:965,y:732,w:116,h:24,rx:12,fs:9.5,label:"AlphaGo · 2016"},
  {id:"rlhf", x:982,y:766,w:108,h:24,rx:12,fs:11,label:"RLHF",variant:"gold",bold:true},

  // ML Outros regimes
  {id:"series-temporais", x:1027,y:826,w:96,h:22,rx:11,fs:9,label:"Séries Temporais"},
  {id:"self-superv-federado", x:1058,y:856,w:110,h:22,rx:11,fs:8,label:"Self-superv. · Federado"},
  {id:"automl", x:1100,y:886,w:80,h:22,rx:11,fs:9,label:"AutoML"},

  // Redes Neurais
  {id:"perceptron", x:1163,y:450,w:140,h:24,rx:12,fs:9.5,label:"Perceptron · 1958"},
  {id:"mlp-backprop", x:1122,y:490,w:162,h:24,rx:12,fs:9.5,label:"MLP · Backprop · 1986"},
  {id:"som", x:1098,y:530,w:140,h:24,rx:12,fs:9.5,label:"SOM (Kohonen)"},
  {id:"hopfield-boltzmann", x:1083,y:570,w:114,h:24,rx:12,fs:8.5,label:"Hopfield · Boltzmann"},

  // Deep Learning
  {id:"visao-cnn", x:1237,y:552,w:174,h:24,rx:12,fs:9.5,label:"Visão Computacional (CNN)"},
  {id:"fala-audicao-rnn", x:1213,y:591,w:164,h:24,rx:12,fs:9.5,label:"Fala · Audição (RNN·LSTM)"},
  {id:"sinais-autoencoders", x:1199,y:630,w:126,h:24,rx:12,fs:9,label:"Sinais · Autoencoders"},
  {id:"gnn", x:1194,y:669,w:104,h:24,rx:12,fs:10,label:"GNN · Grafos"},
  {id:"mod-difusao", x:1193,y:708,w:94,h:24,rx:12,fs:9,label:"Mod. de Difusão"},
  {id:"nerf-3d", x:1203,y:747,w:84,h:24,rx:12,fs:9.5,label:"NeRF · 3D"},

  // IA Generativa (elipse 4, texto claro sobre fundo escuro)
  {id:"gan-vae", x:1345,y:638,w:140,h:22,rx:11,fs:10,label:"GAN · VAE",variant:"dark"},
  {id:"transformers", x:1345,y:665,w:140,h:20,rx:10,fs:9.5,label:"Transformers · 2017",variant:"dark"},

  // LLMs (dentro da caixa dourada)
  {id:"llms", x:1360,y:717,w:136,h:14,rx:6,fs:8,label:"LLMs — clique para detalhes",variant:"gold-label"},
  {id:"llms-gpt", x:1362,y:732,w:38,h:21,rx:10.5,fs:9,label:"GPT",variant:"gold",bold:true,linkId:"llms"},
  {id:"llms-claude", x:1409,y:732,w:38,h:21,rx:10.5,fs:8.5,label:"Claude",variant:"gold",bold:true,linkId:"llms"},
  {id:"llms-gemini", x:1456,y:732,w:38,h:21,rx:10.5,fs:8.5,label:"Gemini",variant:"gold",bold:true,linkId:"llms"},
  {id:"llms-llama", x:1362,y:759,w:38,h:21,rx:10.5,fs:8.5,label:"Llama",variant:"gold",bold:true,linkId:"llms"},
  {id:"llms-deepseek", x:1409,y:759,w:38,h:21,rx:10.5,fs:7,label:"DeepSeek",variant:"gold",bold:true,linkId:"llms"},
  {id:"llms-mistral", x:1456,y:759,w:38,h:21,rx:10.5,fs:8,label:"Mistral",variant:"gold",bold:true,linkId:"llms"},

  {id:"geracao-multimidia", x:1345,y:798,w:140,h:20,rx:10,fs:9.5,label:"Imagem · Vídeo · Áudio · Código",variant:"dark"},

  // IA Agêntica
  {id:"ia-agentica", x:1400,y:912,w:230,h:40,rx:20,fs:12,label:"IA Agêntica · 2024+",variant:"gold-box",sub:"ReAct · Ferramentas · RAG · MCP · Multiagente"},

  // Aplicações
  {id:"app-visao", x:380,y:1048,w:205,h:34,rx:17,fs:13,label:"Visão Computacional"},
  {id:"app-pln", x:601,y:1048,w:205,h:34,rx:17,fs:12,label:"PLN — Linguagem Natural"},
  {id:"app-fala", x:822,y:1048,w:205,h:34,rx:17,fs:13,label:"Fala (ASR · TTS)"},
  {id:"app-robotica", x:1043,y:1048,w:205,h:34,rx:17,fs:13,label:"Robótica & Embodied AI"},
  {id:"app-recomendacao", x:1264,y:1048,w:205,h:34,rx:17,fs:11.5,label:"Sistemas de Recomendação"},
  {id:"app-veiculos", x:1485,y:1048,w:205,h:34,rx:17,fs:13,label:"Veículos Autônomos"},

  // Suporte
  {id:"hardware", x:300,y:1120,w:300,h:44,rx:22,fs:12.5,label:"Hardware: GPU · TPU · NPU · Neuromórfica",variant:"support"},
  {id:"mlops-llmops", x:622,y:1120,w:170,h:44,rx:22,fs:12.5,label:"MLOps / LLMOps",variant:"support"},
  {id:"xai", x:814,y:1120,w:185,h:44,rx:22,fs:12.5,label:"IA Explicável (XAI)",variant:"support"},
  {id:"seguranca-alinhamento", x:1021,y:1120,w:235,h:44,rx:22,fs:12.5,label:"Segurança & Alinhamento",variant:"support"},
  {id:"etica-governanca", x:1278,y:1120,w:345,h:44,rx:22,fs:12.5,label:"Ética · Governança — EU AI Act · PL 2338",variant:"support"}
];

const SVGNS = "http://www.w3.org/2000/svg";

// Cor de preenchimento por classificação de uso (status), não mais por camada estrutural
const STATUS_STYLE = {
  ativa:     {fill:"#DFC067", stroke:"#13293D", sw:1,   textFill:"#13293D", dash:null},
  nicho:     {fill:"#6F8499", stroke:"#13293D", sw:1,   textFill:"#F7F3EB", dash:null},
  historica: {fill:"#E6E3DA", stroke:"#B9B2A3", sw:1,   textFill:"#4A4F55", dash:null},
  fronteira: {fill:"#FDFBF6", stroke:"#C9A227", sw:1.8, textFill:"#13293D", dash:"4 3"}
};

function styleFor(status){
  return STATUS_STYLE[status] || {fill:"#FDFBF6", stroke:"#13293D", sw:1.3, textFill:"#13293D", dash:null};
}

function renderPills(){
  const layer = document.getElementById("pills-layer");
  PILLS.forEach(p => {
    const clickId = p.linkId || p.id;
    const data = TECH[clickId];
    if (!data && p.variant !== "gold-label") { console.warn("Sem dados para:", clickId); }

    const g = document.createElementNS(SVGNS, "g");
    const isActive = data && data.status === "ativa";
    g.setAttribute("class", "tech" + (isActive ? " tech-gold" : ""));
    g.setAttribute("data-id", clickId);
    g.setAttribute("data-status", data ? data.status : "");
    if (p.variant !== "gold-label"){
      g.setAttribute("tabindex", "0");
      g.setAttribute("role", "button");
      g.setAttribute("aria-label", p.label);
    } else {
      g.style.pointerEvents = "none";
    }

    const st = styleFor(data ? data.status : null);

    if (p.variant !== "gold-label"){
      const rect = document.createElementNS(SVGNS, "rect");
      rect.setAttribute("x", p.x); rect.setAttribute("y", p.y);
      rect.setAttribute("width", p.w); rect.setAttribute("height", p.h);
      rect.setAttribute("rx", p.rx);
      rect.setAttribute("fill", st.fill);
      rect.setAttribute("stroke", st.stroke);
      rect.setAttribute("stroke-width", st.sw);
      if (st.dash) rect.setAttribute("stroke-dasharray", st.dash);
      g.appendChild(rect);
    }

    const text = document.createElementNS(SVGNS, "text");
    text.setAttribute("x", p.x + p.w/2);
    text.setAttribute("y", p.y + p.h/2 + (p.fs*0.35));
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("font-size", p.fs);
    text.setAttribute("fill", st.textFill);
    if (p.bold) text.setAttribute("font-weight", "600");
    text.textContent = p.label;
    g.appendChild(text);

    if (p.sub){
      const sub = document.createElementNS(SVGNS, "text");
      sub.setAttribute("x", p.x + p.w/2);
      sub.setAttribute("y", p.y + p.h - 6);
      sub.setAttribute("text-anchor", "middle");
      sub.setAttribute("font-size", 8.5);
      sub.setAttribute("fill", st.textFill);
      sub.textContent = p.sub;
      g.appendChild(sub);
    }

    if (p.variant !== "gold-label"){
      g.addEventListener("click", () => openCard(clickId));
      g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " "){ e.preventDefault(); openCard(clickId); }});
    }
    layer.appendChild(g);
  });
}

// ===== MODAL =====
const backdrop = document.getElementById("backdrop");
const elEyebrow = document.getElementById("card-eyebrow");
const elTitle = document.getElementById("card-title");
const elEra = document.getElementById("card-era");
const elStatus = document.getElementById("card-status");
const elStatusLabel = document.getElementById("card-status-label");
const elDesc = document.getElementById("card-desc");
const elUsesList = document.getElementById("card-uses-list");

function openCard(id){
  const d = TECH[id];
  if (!d) return;
  elEyebrow.textContent = d.group;
  elTitle.textContent = d.name;
  elEra.textContent = d.era;
  elStatus.className = "status-" + d.status;
  elStatusLabel.textContent = d.statusLabel;
  elDesc.textContent = d.desc;
  elUsesList.innerHTML = "";
  d.uses.forEach(u => {
    const li = document.createElement("li");
    li.textContent = u;
    elUsesList.appendChild(li);
  });
  backdrop.classList.add("open");
  document.getElementById("card-close").focus();
}
function closeCard(){
  backdrop.classList.remove("open");
}
document.getElementById("card-close").addEventListener("click", closeCard);
backdrop.addEventListener("click", (e) => { if (e.target === backdrop) closeCard(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeCard(); });

renderPills();

// esconder hint após primeira interação
let hintTimer = setTimeout(()=>{ const h=document.querySelector(".hint"); if(h) h.style.transition="opacity .6s"; if(h) h.style.opacity="0"; }, 7000);
function dismissHint(){ const h=document.querySelector(".hint"); if(h){ h.style.transition="opacity .3s"; h.style.opacity="0"; } clearTimeout(hintTimer); }

// ===== ZOOM / PAN =====
(function(){
  const stage = document.getElementById("zoom-stage");
  const inner = document.getElementById("zoom-inner");
  const MIN_SCALE = 1, MAX_SCALE = 6;
  const state = {scale:1, x:0, y:0};
  const pointers = new Map();
  let isPanning = false, dragMoved = false, panStart = null;
  let pinchStartDist = 0, pinchStartScale = 1, pinchMid = null;

  function clamp(v,min,max){ return Math.max(min, Math.min(max, v)); }

  function clampPan(){
    const rect = stage.getBoundingClientRect();
    const contentW = rect.width * state.scale, contentH = rect.height * state.scale;
    const minX = Math.min(0, rect.width - contentW), maxX = 0;
    const minY = Math.min(0, rect.height - contentH), maxY = 0;
    state.x = clamp(state.x, minX, maxX);
    state.y = clamp(state.y, minY, maxY);
  }

  function applyTransform(){
    inner.style.transform = `translate(${state.x}px, ${state.y}px) scale(${state.scale})`;
  }

  function zoomAt(px, py, newScale){
    newScale = clamp(newScale, MIN_SCALE, MAX_SCALE);
    const lx = (px - state.x) / state.scale;
    const ly = (py - state.y) / state.scale;
    state.scale = newScale;
    state.x = px - newScale * lx;
    state.y = py - newScale * ly;
    clampPan();
    applyTransform();
  }

  function dist(a,b){ return Math.hypot(a.x-b.x, a.y-b.y); }
  function mid(a,b){ return {x:(a.x+b.x)/2, y:(a.y+b.y)/2}; }
  function toStageLocal(clientX, clientY){
    const rect = stage.getBoundingClientRect();
    return {x: clientX - rect.left, y: clientY - rect.top};
  }

  stage.addEventListener("pointerdown", (e) => {
    dismissHint();
    pointers.set(e.pointerId, {x:e.clientX, y:e.clientY});
    inner.classList.remove("smooth");
    if (pointers.size === 1){
      isPanning = true; dragMoved = false;
      panStart = {x:e.clientX, y:e.clientY, sx:state.x, sy:state.y};
      stage.classList.add("panning");
    } else if (pointers.size === 2){
      isPanning = false;
      const pts = Array.from(pointers.values());
      pinchStartDist = dist(pts[0], pts[1]);
      pinchStartScale = state.scale;
      pinchMid = mid(pts[0], pts[1]);
    }
  });

  window.addEventListener("pointermove", (e) => {
    if (!pointers.has(e.pointerId)) return;
    pointers.set(e.pointerId, {x:e.clientX, y:e.clientY});

    if (pointers.size === 1 && isPanning){
      const dx = e.clientX - panStart.x, dy = e.clientY - panStart.y;
      if (Math.hypot(dx,dy) > 6) dragMoved = true;
      state.x = panStart.sx + dx;
      state.y = panStart.sy + dy;
      clampPan();
      applyTransform();
    } else if (pointers.size === 2){
      dragMoved = true;
      const pts = Array.from(pointers.values());
      const d = dist(pts[0], pts[1]);
      const newMid = mid(pts[0], pts[1]);
      const local = toStageLocal(newMid.x, newMid.y);
      const newScale = pinchStartScale * (d / pinchStartDist);
      zoomAt(local.x, local.y, newScale);
    }
  });

  function endPointer(e){
    pointers.delete(e.pointerId);
    if (pointers.size === 0){
      isPanning = false;
      stage.classList.remove("panning");
    } else if (pointers.size === 1){
      const remaining = Array.from(pointers.entries())[0];
      isPanning = true;
      panStart = {x:remaining[1].x, y:remaining[1].y, sx:state.x, sy:state.y};
    }
  }
  window.addEventListener("pointerup", endPointer);
  window.addEventListener("pointercancel", endPointer);

  // impede que um arraste dispare o clique de uma pill
  stage.addEventListener("click", (e) => {
    if (dragMoved){ e.stopPropagation(); dragMoved = false; }
  }, true);


  // duplo clique / duplo toque para zoom rápido
  stage.addEventListener("dblclick", (e) => {
    dismissHint();
    inner.classList.add("smooth");
    const local = toStageLocal(e.clientX, e.clientY);
    if (state.scale > MIN_SCALE * 1.5){
      state.scale = MIN_SCALE; state.x = 0; state.y = 0;
      applyTransform();
    } else {
      zoomAt(local.x, local.y, 2.4);
    }
  });

  // botões de controle
  document.getElementById("zoom-in").addEventListener("click", () => {
    inner.classList.add("smooth");
    const rect = stage.getBoundingClientRect();
    zoomAt(rect.width/2, rect.height/2, state.scale * 1.4);
  });
  document.getElementById("zoom-out").addEventListener("click", () => {
    inner.classList.add("smooth");
    const rect = stage.getBoundingClientRect();
    zoomAt(rect.width/2, rect.height/2, state.scale / 1.4);
  });
  document.getElementById("zoom-reset").addEventListener("click", () => {
    inner.classList.add("smooth");
    state.scale = 1; state.x = 0; state.y = 0;
    applyTransform();
  });

  applyTransform();
})();
