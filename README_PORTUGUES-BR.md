<img width="1912" height="885" alt="JC_ScrapMap" src="https://github.com/user-attachments/assets/6bc95c5b-edf5-4de1-8aee-a3b5d881ada5" />

# JC ScrapMap 0.8.1-rc2

O JC ScrapMap é um mapa auxiliar offline para o modo Survival do Scrap
Mechanic.

Esta versão candidata lê o terreno exato diretamente do banco de dados do save
selecionado. Ele não altera o Scrap Mechanic, não inicia o jogo, não instala
arquivos Lua e não exige privilégios de administrador.

## Como iniciar

1. Extraia a pasta completa.
2. Clique duas vezes em `Start JC ScrapMap.cmd`.
3. O mapa abrirá no navegador padrão.
4. Use o seletor de saves no mapa para alternar entre mundos Survival.

O runtime Python privado incluído é usado automaticamente. Não é necessário
instalar Python.

## Dados exatos

O terreno persistido pelo próprio jogo contém as células já geradas. O JC
ScrapMap abre o SQLite somente para leitura e mostra:

- estradas e suas direções;
- regiões de água/lago;
- deserto;
- floresta queimada;
- Estações de Esquemas.

O hash, tamanho e horário do save são verificados antes e depois da leitura.

## Privacidade

- O servidor local aceita conexões apenas em `127.0.0.1`.
- Nenhum save, marcador, Steam ID ou dado do mapa é enviado.
- Não é necessária conexão com a internet.
- O save nunca é aberto para escrita.
- Notas e estado do mapa ficam dentro da pasta extraída do aplicativo.

## Logs ao vivo e persistentes

A janela do PowerShell permanece aberta enquanto o servidor local do mapa
estiver funcionando e mostra os eventos operacionais ao vivo. Fechar essa
janela encerra o servidor.

Os mesmos eventos ficam registrados em `logs\jc-scrapmap.log`. O arquivo gira
ao atingir 1 MB e mantém três cópias anteriores. Ele não registra conteúdo do
save, usuário do Windows, Steam ID, caminhos pessoais, coordenadas, notas,
marcadores, corpos de requisições HTTP ou conteúdo do terreno.

Esta é a versão candidata `0.8.1-rc2`. Os campos
de prisioneiros e as ruínas comuns podem ser exibidos em camadas separadas,
ambas desativadas por padrão.
