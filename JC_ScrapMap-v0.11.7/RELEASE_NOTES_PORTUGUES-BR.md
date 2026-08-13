# JC ScrapMap 0.11.7 — Notas da Versão

English: `RELEASE_NOTES.md`

## Rescue Vehicle e Instant Recovery

- Adiciona a identificação exata do Rescue Vehicle à camada existente
  **Vehicles**.
- Exige exatamente dois Scrap Gas Engines, sete blocos de Scrap Metal, cinco
  Scrap Wheels, um Scrap Seat comum e um Portable Craftbot, sem qualquer peça
  ou bloco adicional conectado.
- Permite organizar as peças obrigatórias em qualquer formato ou orientação.
- Mostra o Rescue Vehicle com símbolo vermelho e o nome **Rescue Vehicle**; os
  veículos comuns detectados continuam amarelos.
- Adiciona o controle expansível **Instant Recovery** após selecionar um
  veículo detectado.
- **RECOVERY AT YOUR OWN RISK!** move todos os corpos rígidos conectados do
  veículo selecionado para um ponto de referência salvo sete metros acima do
  Rescue Vehicle.
- Preserva posições relativas, juntas, rolamentos, suspensões, controladores,
  peças conectadas e a rotação salva.

## Aviso importante sobre alteração do save

A geração e a consulta normal do mapa continuam sendo somente para leitura. O
Instant Recovery é uma exceção explícita e grava diretamente no save Survival
selecionado.

Feche o Scrap Mechanic e faça backup do save antes de usar a recuperação. Não
existe desfazer automático. Restaure o backup se o mundo ou veículo alterado
não funcionar como esperado.

A rotação é preservada intencionalmente. Um veículo recuperado pode aparecer
ou cair de cabeça para baixo; o recurso não o nivela automaticamente.

## Confiabilidade e compatibilidade

- Identifica novamente o veículo selecionado e o Rescue Vehicle imediatamente
  antes da alteração, sem confiar apenas no estado antigo do navegador.
- Aplica uma única translação a todos os corpos conectados dentro de uma
  transação SQLite imediata.
- Atualiza em conjunto as transformações dos corpos e os limites espaciais do
  SQLite.
- Executa a verificação de integridade do SQLite antes de confirmar a alteração.
- Rejeita seleções antigas, veículos ausentes, registros incompatíveis e saves
  que não contenham exatamente um Rescue Vehicle válido.
- Mantém inalteradas todas as camadas existentes e as visualizações separadas
  de Excavation Island e das áreas subterrâneas.

## Validação

- Passaram os testes da assinatura exata, volume dos blocos e rejeição de peças
  adicionais.
- A translação de veículos com vários corpos preservou rotações, registros da
  construção e o Rescue Vehicle em testes automatizados com cópias descartáveis.
- Passaram as verificações de Python, JavaScript, launcher, regressão das
  camadas, conteúdo do arquivo e atualização usando o runtime incluído.
- O teste manual de recuperação funcionou. Uma queda de cabeça para baixo foi
  observada e aceita como comportamento esperado por preservar a rotação.
