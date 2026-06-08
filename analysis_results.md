# Análise de Falhas no Mapeamento do SimRel

Realizei uma investigação profunda (incluindo buscas diretas no repositório `simrel.build` e nos repositórios oficiais) para entender os motivos exatos que levaram o nosso script a não encontrar os commits destas features.

Como solicitado, começamos dissecando o primeiro caso: o **Eclipse Scout**.

## 1. O caso do SCOUT (Ex: 8.0.0 em 2018-09)

**Por que falhou?** 
A versão registrada nos JSONs originais de entrada para o Scout costuma ser genérica, como `8.0.0` (sem timestamp). Isso acontece porque no arquivo de contribuição (`scout.aggrcon` dentro do repositório `simrel.build`), os mantenedores do Scout definem a versão apenas com o atributo base: `versionRange="8.0.0"`.

No entanto, ao analisar a URL do repositório p2 fornecida no mesmo arquivo `.aggrcon`, encontramos o endereço exato do build:
`http://download.eclipse.org/scout/releases/8.0/8.0.0/021_Simrel_2018_09/`

**A descoberta no Git do Scout:**
Quando fui ao repositório local `scout.rt` e listei as tags da versão 8.0, o Git me retornou:
- `8.0.0.019_Simrel_2018_09_RC1`
- `8.0.0.021_Simrel_2018_09` *(Essa é a tag exata que o p2 usou!)*

**Conclusão para o Scout:** O script falhou porque a heurística procurava por "8.0.0" (ou um timestamp), mas a tag real usada pela equipe de desenvolvimento foi customizada com sufixos verbosos (`.021_Simrel_2018_09`). Além disso, o arquivo `pom.xml` não ajudou o nosso *Pickaxe* porque o Scout é um projeto *Maven-First*, o que significa que o código-fonte carrega a versão como `8.0.0-SNAPSHOT` até o momento do build contínuo.

---

## 2. O caso do ECLIPSELINK (Ex: 3.10.0 a 3.41.0)

**Por que falhou?**
Esse é um falso negativo de roteamento! O JSON original de versões diz que o ECLIPSELINK possui a versão `3.10.0`. No entanto, esse JSON também avisa: *"from WebTools (contains eclipselink features)"*.

**A descoberta no simrel.build:**
Ao checar o arquivo `webtools.aggrcon` correspondente à versão Photon, encontramos a seguinte linha:
`<features name="org.eclipse.jpt.jpa.eclipselink.feature.feature.group">`

Isso significa que a versão mapeada no JSON não é a versão do motor EclipseLink (código-fonte da fundação EclipseLink), mas sim a versão do **plugin de integração do EclipseLink para o WTP** (Java Persistence Tools - JPT). Esse código não reside no repositório `eclipselink` que configuramos no script, mas sim dentro do monorepo do **WebTools** (`webtools.javaee`)!
Como o script foi configurado para buscar a versão `3.10.0` no repositório `eclipselink` local, ele varreu o histórico inteiro e não achou nada, estourando o *Timeout de 30s*.

---

## 3. O caso do DATATOOLS (DTP) e WEBTOOLS (WTP)

Para o DTP (Ex: `1.14.103` em 2018-12) e WTP, o problema se divide em dois vetores:

**Vetor A - Nomenclatura SNAPSHOT no P2:**
Analisando o `dtp.aggrcon` do `simrel.build`, os mantenedores apontam para:
`http://download.eclipse.org/datatools/updates/1.14.103-SNAPSHOT/repository/`
Isso indica que o projeto DataTools em 2018 estava utilizando builds "vivas" de snapshot sem carimbar tags definitivas no Git principal para cada pacote do SimRel. Como não há timestamp ou tag exata, a busca de histórico profunda precisa ser perfeita.

**Vetor B - Timeout em Repositórios Mastodônticos:**
O DTP e o WTP têm mais de uma década e meia de código herdado. O nosso *Pickaxe* do script Python executa o comando `git log -S "Bundle-Version: 1.14.103"`. Encontrar essa agulha no palheiro da árvore completa do WTP leva minutos, o que engatilhava a nossa trava de segurança de `Timeout` e retornava nulo para não congelar sua máquina.

---

### Soluções Possíveis

Se você desejar fechar essa lacuna de mapeamento para esses componentes específicos, teremos que programar heurísticas "hardcoded":
1. **Para o Scout:** Alterar a lógica para procurar por padrões de tags que contenham `_Simrel_<Release>` ou o sufixo numérico de build contínuo.
2. **Para o EclipseLink:** Redirecionar a busca da feature `ECLIPSELINK` para o repositório `webtools.javaee`, e não o `eclipselink` nativo.
3. **Para WTP/DTP:** Aumentar o timeout e rodar isoladamente, ou usar `git ls-remote` nas URLs contidas nos arquivos `.aggrcon` do `simrel.build` para inferir as datas do build P2.
