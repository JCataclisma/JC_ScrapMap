<img width="1912" height="885" alt="JC_ScrapMap" src="https://github.com/user-attachments/assets/6bc95c5b-edf5-4de1-8aee-a3b5d881ada5" />

# JC ScrapMap 0.11.7

O JC ScrapMap é um mapa auxiliar offline para o modo Survival do Scrap
Mechanic.

Ele lê o terreno gerado, posições salvas, veículos, progressão e outras
informações diretamente do save Survival selecionado. A versão 0.11.7 também
adiciona a ação opcional **Instant Recovery**, que pode reposicionar um veículo
salvo acima de um Rescue Vehicle construído especialmente para isso.

English: `README.md`

## Aviso importante: faça backup do save

A consulta normal do mapa continua sendo somente para leitura. O **Instant
Recovery é diferente: ele altera o banco de dados do save selecionado quando a
ação final de recuperação é clicada.**

Antes de usar o Instant Recovery:

1. Feche completamente o Scrap Mechanic.
2. Faça backup do save Survival que será alterado.
3. Confirme que o save correto está selecionado no JC ScrapMap.
4. Guarde o backup até carregar e salvar o mundo recuperado com sucesso.

Não existe desfazer dentro do aplicativo. Se o resultado não for aceitável,
restaure o backup.

## Como iniciar

1. Extraia a pasta completa `JC_ScrapMap-v0.11.7`.
2. Clique duas vezes em `Start JC ScrapMap.cmd`.
3. O mapa abrirá no navegador padrão.
4. Use **Available saves** para trocar de mundo Survival, se necessário.

Para uma janela auxiliar sempre visível, use
`Start JC ScrapMap Overlay.cmd`. Ele pode usar Chrome, Brave, Vivaldi,
Chromium, Opera, Microsoft Edge ou outro navegador compatível da família
Chromium já instalado. O JC ScrapMap não inclui nem instala navegador.

O runtime Python privado incluído é usado automaticamente. Não é necessário
instalar Python nem usar privilégios de administrador.

## Como construir o Rescue Vehicle

O Rescue Vehicle pode ter qualquer formato ou orientação. Todas as peças
obrigatórias devem pertencer à mesma construção móvel conectada.

Ele deve conter exatamente e somente:

- 2 Scrap Gas Engines;
- 7 blocos de Scrap Metal;
- 5 Scrap Wheels;
- 1 Scrap Seat comum — não use o Scrap Driver's Seat;
- 1 Portable Craftbot.

Nada mais pode estar conectado. Os sete blocos de Scrap Metal podem ser
organizados em qualquer formato. Quando identificado, ele aparece como um
símbolo vermelho **Rescue Vehicle** na camada existente **Vehicles**. Os
veículos comuns continuam amarelos.

## Como usar o Instant Recovery

1. Feche o Scrap Mechanic e faça backup do save selecionado.
2. Inicie o JC ScrapMap e selecione o save correto.
3. Ative a camada **Vehicles**.
4. Confirme que o **Rescue Vehicle** vermelho aparece onde foi construído.
5. Clique no símbolo amarelo do veículo que deseja recuperar.
6. Na barra lateral esquerda, abra **Instant Recovery**.
7. Clique uma vez em **RECOVERY AT YOUR OWN RISK!**.
8. Feche o JC ScrapMap, inicie o Scrap Mechanic e carregue o save alterado.

A construção conectada inteira é movida para que seu ponto de referência salvo
fique sete metros acima do Rescue Vehicle. Rolamentos, suspensões, corpos
conectados, controladores, peças, posições relativas e a rotação salva do
veículo são preservados.

Como a rotação é preservada e o veículo é solto acima do destino, ele pode
aparecer ou cair de cabeça para baixo. Isso é esperado. O Instant Recovery não
nivela nem gira o veículo automaticamente.

## Recursos do mapa

O mapa offline inclui, quando disponíveis no save selecionado:

- estradas direcionais e regiões do terreno;
- água, deserto, floresta queimada e floresta de outono;
- Schematic Stations e Warehouses comuns;
- missões do construtor, poços de óleo/químicos, campos de prisioneiros e ruínas;
- entradas subterrâneas, progressão, resumos e mapas aproximados dos andares;
- mapa separado da superfície de Excavation Island;
- posição salva do jogador, beacons físicos, notas e veículos detectados.

A maioria das camadas que revelam informações, incluindo **Vehicles**, começa
desativada.

## Privacidade e dados locais

- O servidor web aceita conexões somente em `127.0.0.1`.
- Nenhum save, marcador, coordenada, Steam ID ou dado do mapa é enviado.
- Não é necessária conexão com a internet.
- A consulta normal abre o save somente para leitura.
- Apenas a ação explícita Instant Recovery abre o save selecionado para uma
  alteração local e atômica.
- Estado gerado, notas, preferências do navegador e logs permanecem dentro da
  pasta extraída do aplicativo.

## Logs

A janela do PowerShell permanece aberta enquanto o servidor local está em
execução. Fechar essa janela encerra o JC ScrapMap.

Os eventos operacionais são gravados em `logs\jc-scrapmap.log`. O log rotativo
não inclui conteúdo do save, usuário do Windows, Steam ID, nome do save,
caminhos pessoais completos, coordenadas do jogador, conteúdo das notas ou
corpos das requisições HTTP.

## Limitações da recuperação

- A recuperação usa o último estado gravado no save; não é um teleporte ao vivo.
- O Scrap Mechanic deve permanecer fechado durante a alteração.
- A construção selecionada ainda precisa corresponder ao veículo mostrado no mapa.
- Deve existir exatamente um Rescue Vehicle válido no save selecionado.
- A orientação é preservada; o resultado pode ficar de cabeça para baixo.
- Restaure o backup se o mundo ou a construção não funcionar como esperado.
