# Rede de coautoria — Revista de Educação Matemática (REMat-SP)

Visualização interativa da rede de coautoria da
[Revista de Educação Matemática](https://www.revistasbemsp.com.br/index.php/REMat-SP),
reimplementando em Python o método de **Rafael Gutierres Castanha** (2024) —
*Visualização de redes de coautoria como insumo bibliométrico às revistas
científicas: uma proposta via web scraping para os periódicos Em Questão e
Encontros Bibli* (DOI: [10.5007/1518-2924.2024.e96589](https://doi.org/10.5007/1518-2924.2024.e96589)).

## Demonstração

A rede interativa está publicada em:
**https://remat-rede-coautoria.gerlanmatfis.workers.dev**

## Funcionalidades

- **Raspagem** do portal OJS da revista (30 números, 466 artigos, 775 autores).
- **Busca por nome** com destaque da sub-rede do autor (e seus coautores).
- **Métricas** de análise de redes sociais, colorizáveis por autor:
  produção (artigos), grau, intermediação (betweenness), proximidade (closeness),
  autovetor (eigenvector) e agrupamento (clustering).
- **Detecção de comunidades** (Louvain) com destaque por comunidade.
- **Tabela dinâmica** dos 20 autores mais bem posicionados na métrica escolhida.
- Rede **self-contained**: a biblioteca vis-network está incluída no repositório
  (sem dependência de CDN externo).

## Estrutura

```
remat_coautoria.py          # raspagem OJS + rede básica (requests + BeautifulSoup)
remat_ferramentas.py        # métricas, comunidades e geração do HTML interativo
remat_dados_coautoria.json  # dados raspados (artigos, produção, arestas)
site/
  index.html                # rede interativa (self-contained)
  vis-network.min.js        # biblioteca vis-network (visjs)
```

## Como reproduzir

Requisitos: Python 3.10+ e as libs `requests`, `beautifulsoup4`, `networkx`.

```bash
pip install requests beautifulsoup4 networkx

# 1. raspa a revista e gera remat_dados_coautoria.json
python remat_coautoria.py

# 2. calcula métricas/comunidades e gera site/index.html
python remat_ferramentas.py
```

O portal da REMat-SP usa um desafio anti-bot ("humans_21909"); o script define o
cookie correspondente para acessar as páginas.

## Condição de funcionamento para outras revistas

O método funciona em qualquer periódico construído com o **Open Journal System
(OJS)**, que padroniza a estrutura de URLs (`/issue/archive`, `/issue/view/N`) e as
classes CSS `.title` (títulos dos números) e `.authors` (autores de cada artigo).
Ajustes necessários por revista:

1. confirmar que é OJS (`<meta name="generator" content="Open Journal Systems ...">`);
2. verificar `/robots.txt` e os termos de uso antes de raspar;
3. ajustar o seletor interno dos nomes de autores (aqui: `div.authors span.name`);
4. tratar paginação do arquivo e eventuais cookies/anti-bot.

## Publicação (GitHub Pages do Cloudflare)

A pasta `site/` é um site estático: qualquer host serve. A configuração de deploy
está em `wrangler.jsonc`. Para publicar no Cloudflare Pages (Workers):

```bash
npx wrangler deploy
```

## Licença

Conteúdo da revista sob CC BY 4.0 (licença do periódico). Código deste repositório
disponível para reuso acadêmico; cite o artigo original de Castanha (2024) e este
repositório.
