# JC ScrapMap 0.12.7 — Notas da Versão

English: `RELEASE_NOTES.md`

## Restauração única de Warehouse regular

- Adiciona **Warehouse Revival** aos Warehouses regulares destruídos na camada
  Warehouses/Schematics; Warehouses de missão ficam excluídos.
- Remove do exterior o estado de destruição e explosão para que a estrutura
  intacta retorne no próximo carregamento do save.
- Desconecta os andares e elevadores destruídos para que o Scrap Mechanic crie
  novos mundos internos na próxima entrada.
- Preserva portais externos unilaterais de entrada e saída de emergência, além
  da saída normal do elevador capaz de se reconectar. Isso usa os fluxos normais
  de reconexão de um Warehouse novo em uma célula de overworld já criada.
- Registra cada restauração nos dados locais do mapa e recusa qualquer nova
  restauração daquele Warehouse.
- Executa todas as alterações em uma transação SQLite protegida e verifica a
  integridade do banco antes de confirmar.

## Recycler externo

- Adiciona um Recycler externo operado pelo JC ScrapMap, sem instalar mod nem
  adicionar uma mecânica nativa ao jogo.
- Identifica uma construção móvel conectada exata contendo somente sete blocos
  de Scrap Metal, sete blocos de Scrap Wood, um Portable Craftbot, três Large
  Chests e dois Toilet Papers.
- Mostra as construções identificadas como marcadores verdes **Recycler** em
  uma camada própria do mapa.
- Lê as receitas instaladas do Portable Craftbot, Workbench e Craftbot mesmo
  que o jogador ainda não as tenha desbloqueado.
- Reduz recursivamente os itens fabricados válidos aos recursos das receitas e
  devolve 50% do total combinado, arredondado para itens inteiros.
- Preserva itens sem receita compatível e inequívoca e itens que contenham
  dados especiais de instância.

## Inventário combinado dos três baús

- Trata os três Large Chests como um único inventário de saída com 90 slots.
- Preenche primeiro as pilhas compatíveis existentes e depois os slots livres,
  em uma ordem determinística entre os baús e respeitando os limites de pilha
  instalados.
- Calcula o inventário final completo antes de fazer qualquer alteração.
- Recusa toda a operação quando não existe devolução válida ou quando todos os
  recursos não cabem. Nunca realiza uma reciclagem parcial.

## Segurança da prévia e da transação

- Adiciona uma prévia detalhada dos itens consumidos, recursos devolvidos,
  itens incompatíveis e slots ocupados antes e depois da reciclagem.
- Exige o token exato da prévia durante a execução e recusa alterações nos
  baús ou no Recycler após a prévia.
- Identifica novamente a construção exata e os três containers conectados
  imediatamente antes da gravação.
- Atualiza os três containers em uma única transação SQLite imediata, com
  proteções de comparação durante cada atualização.
- Verifica a integridade do SQLite antes da confirmação e desfaz todas as
  alterações se qualquer validação ou gravação falhar.

## Receita do Recycler

A construção móvel conectada obrigatória deve conter exatamente e somente:

- 7 blocos de Scrap Metal;
- 7 blocos de Scrap Wood;
- 1 Portable Craftbot;
- 3 Large Chests;
- 2 Toilet Papers.

Itens colocados dentro dos baús não contam como peças conectadas à construção.

## Compatibilidade

- Mantém inalterados o Instant Recovery, a atualização manual da posição salva
  do jogador, as camadas existentes, os mapas subterrâneos e Excavation Island.
- A consulta normal do mapa continua somente para leitura. Apenas a execução
  explícita do Recycler e o Instant Recovery gravam no save selecionado.
- Continua offline e usa somente os dados instalados do jogo e o save local
  selecionado.

## Validação

- O Warehouse Revival passou por teste transacional em uma cópia descartável e
  por teste completo da API local. Foram verificadas as alterações no exterior,
  portais, elevadores, contagem regressiva e registro de Warehouses; o Warehouse
  de missão permaneceu inalterado.
- A integridade SQLite foi aprovada, uma segunda restauração foi recusada e o
  SHA-256 do save original permaneceu inalterado durante todos os testes.
- O teste no jogo confirmou exterior, interiores novos, inimigos, elevador de
  entrada, elevador interno e a cadeia normal do elevador final. Depois revelou
  a ausência dos portais de saída de emergência; a estratégia v3 e o reparo
  passaram nos testes com cópia descartável e integridade SQLite, restando a
  confirmação final da saída de emergência dentro do jogo.
- O teste prático com o Recycler planejado funcionou no save Survival alvo.
- O lote de teste reciclou 16 itens em 44 Scrap Metal, 125 Scrap Wood,
  10 Scrap Stone, 2 Pigment Flowers e 2 Soil Bags, reduzindo os slots ocupados
  de 10 para 5.
- O teste com uma cópia descartável confirmou a mesma saída, preservou o
  Recycler e passou na verificação de integridade do SQLite.
- Passaram os testes automatizados de assinatura exata, rejeição de peças
  adicionais, três containers conectados de 30 slots, recuperação recursiva de
  50%, preservação de itens incompatíveis, recusa por falta de espaço, rejeição
  de prévia antiga e gravação atômica.
- Passaram as regressões existentes de identificação de veículos, Instant
  Recovery, snapshot da posição do jogador e interface.
