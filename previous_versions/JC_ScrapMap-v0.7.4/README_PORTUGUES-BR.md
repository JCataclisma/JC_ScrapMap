# JC ScrapMap 0.7.4

JC ScrapMap é um mapa auxiliar offline para Scrap Mechanic 1.0 Survival. Ele lê
seus saves sem modificá-los e abre o mapa no navegador.

## Como iniciar

Dê dois cliques em `Start JC ScrapMap.cmd`. Não é necessário instalar Python.
Mantenha todos os arquivos juntos na pasta extraída.

## Menu

1. **Open map** abre ou atualiza o mapa sem modificar o jogo.
2. **Generate exact roads** inicia o jogo e captura roads, Water, Desert, Burnt
   forest e Schematic Stations. Carregue o mundo desejado e depois feche o
   jogo. Ao terminar, volte ao menu principal e escolha **Open map**. O mapa
   não será mais aberto automaticamente.
3. **Disable/repair road helper** restaura o helper após uma interrupção.
4. **Show road-helper status** mostra o estado atual do helper.
5. **Open diagnostic report** abre o relatório de diagnóstico no Bloco de
   Notas.
6. **Exit** fecha o menu.

A janela de geração permanece aberta mostrando **SUCCESS** ou o erro até você
pressionar Enter.

Antes de mostrar `SUCCESS`, a versão 0.7.4 grava o resultado de forma atômica e
abre novamente o arquivo final para confirmar a seed e todas as contagens. O
relatório mostra uma etapa `IMPORT` quando essa validação termina.

A versão 0.7.4 também corrige o erro `Unknown save identity` ao alternar entre
vários saves. As identidades agora permanecem estáveis quando o jogo atualiza o
save, e a lista é verificada novamente a cada seleção. Se outra pasta extraída
do JC ScrapMap já estiver usando a porta local, o launcher mostra uma mensagem
clara em vez de conectar silenciosamente ao processo errado.

## Relatório para suporte

Após cada tentativa de geração, o arquivo
`JC_ScrapMap_Diagnostic.txt` é criado na pasta principal do JC ScrapMap.
Também é possível abri-lo pela opção 5 do menu.

Esse relatório pode ser enviado junto com um pedido de ajuda. Ele informa as
etapas, a seed, as contagens e o erro ocorrido. Ele não contém o conteúdo do
save, coordenadas do jogador, anotações, Steam ID ou nomes de pastas pessoais.

## Segurança

O helper modifica temporariamente um script de terrain, somente após a escolha
explícita da opção 2 e a autorização de administrador. O arquivo original é
copiado, verificado por hash e restaurado após o jogo fechar. Os bancos de dados
dos saves são sempre abertos em modo somente leitura.

Se a geração for interrompida e o status indicar `ENABLED` ou
`RECOVERY REQUIRED`, feche o jogo e use a opção 3 antes de apagar a pasta.

O programa funciona offline, não possui analytics, tracking, anúncios ou
uploads, e seu servidor local escuta apenas em `127.0.0.1`.
