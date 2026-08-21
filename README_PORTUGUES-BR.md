<img width="1912" height="885" alt="JC_ScrapMap" src="https://github.com/user-attachments/assets/6bc95c5b-edf5-4de1-8aee-a3b5d881ada5" />

# JC ScrapMap 0.12.7

O JC ScrapMap é um mapa auxiliar offline para o modo Survival do Scrap
Mechanic.

Ele lê o terreno gerado, posições salvas, veículos, progressão e outras
informações diretamente do save Survival selecionado. A versão 0.12.7 adiciona
uma restauração única para Warehouses regulares destruídos. Ela restaura o
exterior e permite que o jogo crie novos andares internos. Warehouses de
missão nunca são elegíveis.

English: `README.md`

## Aviso importante: faça backup do save

A consulta normal do mapa continua sendo somente para leitura. **Warehouse
Revival, Recycler e Instant Recovery são ações explícitas que alteram o save.**

Antes de usar qualquer uma dessas ações:

1. Feche completamente o Scrap Mechanic.
2. Faça backup do save Survival que será alterado.
3. Confirme que o save correto está selecionado no JC ScrapMap.
4. Guarde o backup até carregar e salvar o mundo alterado com sucesso.

Não existe desfazer dentro do aplicativo. Se o resultado não for aceitável,
restaure o backup.

## Como iniciar

1. Extraia a pasta completa `JC_ScrapMap-v0.12.7`.
2. Clique duas vezes em `Start JC ScrapMap.cmd`.
3. O mapa abrirá no navegador padrão.
4. Use **Available saves** para trocar de mundo Survival, se necessário.

Para uma janela auxiliar sempre visível, use
`Start JC ScrapMap Overlay.cmd`. Ele pode usar Chrome, Brave, Vivaldi,
Chromium, Opera, Microsoft Edge ou outro navegador compatível da família
Chromium já instalado. O JC ScrapMap não inclui nem instala navegador.

O runtime Python privado incluído é usado automaticamente. Não é necessário
instalar Python nem usar privilégios de administrador.

## Como construir o Recycler

Todas as peças obrigatórias devem pertencer a uma única construção móvel
conectada. O formato e a orientação não importam.

Ele deve conter exatamente e somente:

- 7 blocos de Scrap Metal;
- 7 blocos de Scrap Wood;
- 1 Portable Craftbot;
- 3 Large Chests;
- 2 Toilet Papers.

Nada mais pode estar conectado. Os itens guardados dentro dos três baús são
conteúdo, não peças conectadas à construção, e por isso não invalidam o
Recycler. Quando identificado, ele aparece como um símbolo verde **Recycler**
em sua própria camada do mapa.

## Como usar o Recycler

1. Coloque os itens que deseja reciclar em qualquer um dos três Large Chests.
2. Feche o Scrap Mechanic e faça backup do save selecionado.
3. Inicie o JC ScrapMap e selecione o save correto.
4. Selecione o marcador verde **Recycler**.
5. Abra **External Recycler** e clique em **Preview recycling**.
6. Confira os itens de entrada, os recursos devolvidos e a capacidade dos baús.
7. Clique em **RECYCLE AT YOUR OWN RISK!** somente se a prévia estiver correta.
8. Feche o JC ScrapMap, inicie o Scrap Mechanic e carregue o save alterado.

O Recycler lê os arquivos de receitas instalados do Portable Craftbot,
Workbench e Craftbot, mesmo que o jogador ainda não tenha desbloqueado as
receitas. Itens fabricáveis são reduzidos recursivamente aos recursos de suas
receitas. Depois de reunir todas as entradas válidas, o Recycler devolve 50%
do total de cada recurso, arredondando para baixo até itens inteiros.

Os três Large Chests funcionam como um inventário único de 90 slots. Pilhas
compatíveis existentes são preenchidas primeiro; depois são usados os slots
vazios dos três baús. Itens incompatíveis permanecem nos slots originais. Se
nada puder ser reciclado, ou se todos os recursos devolvidos não couberem, nada
será alterado. Uma prévia antiga ou alterada também é recusada. Uma reciclagem
bem-sucedida atualiza os três baús em uma única transação atômica e verifica a
integridade do SQLite antes de confirmar a alteração.

## Como atualizar a posição salva do jogador

1. Selecione o marcador azul **Last saved player position**.
2. Clique em **Update saved player position** na barra lateral esquerda.

O aplicativo cria uma cópia local descartável e lê somente o registro do
jogador. O marcador e o horário são atualizados sem reconstruir o mapa inteiro.
Essa é a posição mais recente gravada no save, não uma posição ao vivo da
memória do jogo.

## Como construir o Rescue Vehicle

O Rescue Vehicle deve conter exatamente e somente:

- 2 Scrap Gas Engines;
- 7 blocos de Scrap Metal;
- 5 Scrap Wheels;
- 1 Scrap Seat comum — não use o Scrap Driver's Seat;
- 1 Portable Craftbot.

Todas as peças devem formar uma única construção móvel conectada. Ele aparece
como um símbolo vermelho **Rescue Vehicle** na camada **Vehicles**.

## Como usar o Instant Recovery

Feche o Scrap Mechanic, faça backup do save, selecione o marcador amarelo do
veículo, abra **Instant Recovery** e clique em **RECOVERY AT YOUR OWN RISK!**.
A construção conectada inteira é movida sete metros acima do Rescue Vehicle,
preservando peças, juntas, posições relativas, controladores e a rotação salva.
Como a rotação é preservada, o veículo pode aparecer ou cair de cabeça para
baixo.

## Recursos do mapa

O mapa offline inclui, quando disponíveis:

- estradas direcionais e regiões do terreno;
- água, deserto, floresta queimada e floresta de outono;
- Schematic Stations e Warehouses comuns;
- missões do construtor, poços de óleo/químicos, campos de prisioneiros e ruínas;
- entradas subterrâneas, progressão, resumos e mapas aproximados dos andares;
- mapa separado da superfície de Excavation Island;
- posição salva do jogador, beacons físicos, notas, veículos detectados,
  Rescue Vehicle e Recycler.

## Privacidade e dados locais

- O servidor web aceita conexões somente em `127.0.0.1`.
- Nenhum save, marcador, coordenada, Steam ID ou dado do mapa é enviado.
- Não é necessária conexão com a internet.
- A consulta normal abre o save somente para leitura.
- A atualização da posição lê somente uma cópia local descartável.
- Apenas a execução explícita do Recycler e o Instant Recovery abrem o save
  selecionado para uma alteração local e atômica.
- Estado gerado, notas, preferências do navegador e logs permanecem dentro da
  pasta extraída do aplicativo.

## Logs

A janela do PowerShell permanece aberta enquanto o servidor local está em
execução. Fechar essa janela encerra o JC ScrapMap.

Os eventos operacionais são gravados em `logs\jc-scrapmap.log`. O log rotativo
não inclui conteúdo do save, usuário do Windows, Steam ID, nome do save,
caminhos pessoais completos, coordenadas do jogador, conteúdo das notas ou
corpos das requisições HTTP.

## Limitações das alterações do save

- O Scrap Mechanic deve permanecer fechado durante a alteração.
- As duas ações usam o último estado gravado no save, não a memória ao vivo.
- A construção selecionada ainda deve corresponder ao que foi exibido na prévia.
- O Recycler usa receitas instaladas compatíveis e arredondamento para itens
  inteiros; itens incompatíveis são preservados.
- O Instant Recovery preserva a orientação do veículo, inclusive se estiver de
  cabeça para baixo.
- Restaure o backup se o mundo alterado não funcionar como esperado.
