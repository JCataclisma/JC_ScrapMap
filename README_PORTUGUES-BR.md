<img width="1912" height="885" alt="JC_ScrapMap" src="https://github.com/user-attachments/assets/5d9740ca-3139-4ab4-8b2c-22553feff3fc" />
# JC ScrapMap 0.7.1

JC ScrapMap é um mapa offline auxiliar para **Scrap Mechanic 1.0 Survival**.
Ele lê o seu save sem modificá-lo e abre o mapa no seu navegador web padrão.

## Antes de Começar

Você precisa de:

* Windows 10 64-bit ou mais recente
* Scrap Mechanic 1.0 via Steam
* Um navegador web moderno

Mantenha toda esta pasta junta. Não mova arquivos individuais para fora dela.
Não é necessário instalar Python nem qualquer outra ferramenta de programação. O JC ScrapMap inclui seu próprio runtime privado e não o instala no Windows.

## Start

Dê um duplo clique em:

`Start JC ScrapMap.cmd`

O launcher encontra automaticamente a instalação padrão do Scrap Mechanic e os saves do jogador. Se houver mais de um perfil, ele pedirá que você escolha um.

O Scrap Mechanic pode estar instalado em qualquer biblioteca da Steam. O
launcher consulta a instalação registrada da Steam e todos os caminhos em
`steamapps\libraryfolders.vdf`. Se o helper ainda não localizar o jogo, ele
solicita a pasta completa de instalação do Scrap Mechanic.

## The Two Main Menu Options

### 1. Open map

Use sempre que quiser visualizar ou atualizar o mapa.

* Abre o save selecionado em modo **read-only**
* Atualiza a última posição registrada pelo Scrap Mechanic no save
* Atualiza os Beacons físicos construídos pelo jogador, incluindo ícones e cores
* Nunca ativa o road helper
* Não requer permissões de administrador
* Funciona enquanto o jogo está rodando (desde que já tenha salvo dados)
* Se o mapa já estiver aberto no navegador, ele apenas atualiza em vez de iniciar um segundo map server

O símbolo azul do jogador significa **Last saved player position**. Não é GPS em tempo real: o jogo decide quando salvar a posição.

### 2. Generate exact roads

Normalmente use **apenas uma vez para cada seed diferente** de mundo Survival.
Se dois saves usam a mesma seed, podem compartilhar o mesmo road map.

Repita apenas quando:

* mapear um save com seed diferente
* uma atualização futura do jogo alterar a geração do mundo
* um mapa antigo ainda não possuir as regiões de terreno ou as Schematic Stations

Antes de escolher esta opção, feche o Scrap Mechanic. O Windows pedirá permissão de administrador porque este processo modifica temporariamente um script de terrain.

Depois:

1. O launcher faz backup e gera hash do script original
2. Instala temporariamente o JC ScrapMap road exporter
3. O Scrap Mechanic inicia
4. Carregue o mundo Survival desejado
5. Aguarde até o launcher indicar que roads, regiões de terreno e Schematic Stations foram capturados
6. Feche o jogo
7. O launcher restaura o script original, verifica o hash e remove o exporter temporário

Após a limpeza, o jogo volta ao normal sem carregar o JC ScrapMap.

A geração ocorre em uma janela de progresso separada, portanto o menu principal
continua respondendo. Water, Desert e Burnt forest compartilham uma única layer
desmarcada chamada **Terrain regions**, mantendo cores diferentes. As Schematic
Stations capturadas aparecem na layer existente e desmarcada de POIs/spoilers.

## If Option 2 Is Interrupted

Se o Scrap Mechanic fechar ou travar antes da captura, a janela de progresso
detecta a interrupção e tenta executar automaticamente a limpeza verificada. Se
o Windows, Steam ou o computador encerrar a própria janela do helper, feche o
jogo e selecione:

`3. Disable/repair road helper`

Faça isso antes de apagar a pasta do JC ScrapMap ou abrir o jogo novamente.
A cópia de recuperação em `.road-helper` é necessária até finalizar o reparo.

A option 4 mostra se o road helper está ativo.

## Local Data

O JC ScrapMap cria estas pastas:

* `imports` — roads, regiões de terreno e Schematic Stations exatas por seed
* `mapper-data` — dados do mapa por save e suas anotações
* `generated` — estado atual exibido no navegador
* `.road-helper` — dados temporários de recuperação

O banco de dados de saves do Scrap Mechanic nunca é alterado.

## Privacy and Networking

* Totalmente offline após o download
* Sem analytics ou tracking
* Sem advertisements
* Sem uploads
* Sem remote map server
* O browser server roda apenas em `127.0.0.1`
* O runtime interno é usado apenas dentro da pasta

## Closing and Removing

Feche o map-server com `Ctrl+C` na janela do PowerShell.

Antes de remover o programa, use a option 4.
Se estiver `ENABLED`, feche o jogo e execute a option 3 primeiro.
Quando estiver `disabled`, você pode apagar a pasta com segurança.

Consulte `SAFETY_AND_REMOVAL.md` para detalhes completos.

## Source Inspection

O JC ScrapMap inclui código-fonte legível em:

* PowerShell
* Python
* Lua
* JavaScript
* HTML
* CSS
* JSON

Veja `SOURCE.md`.

O pacote também inclui o runtime oficial do CPython 3.14.6 (64-bit) em `runtime/python`.
A licença está em `runtime/python/LICENSE.txt`.
Os jogadores não precisam instalar ou configurar nada.

Veja `THIRD_PARTY_NOTICES.md` para origem oficial e hash de verificação.

## License

Esta versão ainda não declara uma licença open-source.
A presença pública no GitHub permite inspeção, mas não autoriza redistribuição ou modificação do código.
Adicione uma licença explícita antes de divulgar como open source.
