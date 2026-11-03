#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rede de coautoria da Revista de Educação Matemática (REMat-SP)
---------------------------------------------------------------
Reimplementação em Python do método de Rafael Castanha (2024) — "Visualização
de redes de coautoria como insumo bibliométrico às revistas científicas".

Fluxo original (R/rvest -> igraph -> visNetwork):
   1. ler a página de arquivo (/issue/archive);
   2. identificar os links dos volumes/números pela classe CSS ".title";
   3. entrar em cada número e extrair os autores pela classe ".authors";
   4. montar a matriz de coautoria (grafo) e visualizar.

Aqui o mesmo fluxo é feito com requests + BeautifulSoup + networkx e a rede é
salva como HTML interativo (vis-network via CDN, equivalente ao visNetwork).

Condição de funcionamento para outras revistas: a revista precisa usar o
Open Journal System (OJS), que padroniza as classes ".title" (títulos dos
números) e ".authors" (autores de cada artigo). Variações de tema podem exigir
ajustar os seletores (ex.: aqui os nomes estão em "div.authors span.name").

Obs.: este site usa um desafio anti-bot ("humans_21909"). Passamos o cookie
correspondente para acessar as páginas.
"""

import re
import time
import json
from collections import defaultdict, Counter

import requests
from bs4 import BeautifulSoup
import networkx as nx

BASE = "https://www.revistasbemsp.com.br/index.php/REMat-SP"
ARCHIVE = f"{BASE}/issue/archive"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

# ---------------------------------------------------------------------------
# 1. Acesso (contorna o desafio "humans_21909" definindo o cookie)
# ---------------------------------------------------------------------------
session = requests.Session()
session.headers.update(HEADERS)
session.cookies.set("humans_21909", "1", domain="www.revistasbemsp.com.br")


def get(url, retries=3):
    for attempt in range(retries):
        r = session.get(url, timeout=30)
        if r.status_code == 200:
            return r
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Falha ao acessar {url} (status {r.status_code})")


# ---------------------------------------------------------------------------
# 2. Página de arquivo -> links dos números (classe ".title")
# ---------------------------------------------------------------------------
print("Lendo página de arquivo...")
html_archive = BeautifulSoup(get(ARCHIVE).text, "html.parser")

issue_links = []
for a in html_archive.select("a.title"):
    href = a.get("href", "")
    if "/issue/view/" in href:
        issue_links.append(href)

# remove duplicados e ordena pelo id numérico do número
issue_links = sorted(set(issue_links), key=lambda u: int(re.search(r"/view/(\d+)", u).group(1)))
print(f"  -> {len(issue_links)} números encontrados.")

# ---------------------------------------------------------------------------
# 3. Para cada número -> extrai os autores de cada artigo (classe ".authors")
# ---------------------------------------------------------------------------
# articles[i] = lista de nomes de autores do artigo i
articles = []          # lista de listas de autores
issue_articles = {}    # id do número -> quantidade de artigos

for n, link in enumerate(issue_links, 1):
    issue_id = re.search(r"/view/(\d+)", link).group(1)
    html_issue = BeautifulSoup(get(link).text, "html.parser")

    count = 0
    for block in html_issue.select("div.authors"):
        # nomes em <span class="name">; limpa ORCID/Lattes (sup) e espaços
        names = []
        for span in block.select("span.name"):
            name = span.get_text(" ", strip=True)
            name = name.replace("\xa0", " ").strip()
            name = re.sub(r"\s+", " ", name)
            if name:
                names.append(name)
        if names:
            articles.append(names)
            count += 1

    issue_articles[issue_id] = count
    print(f"  [{n:2d}/{len(issue_links)}] número {issue_id}: {count} artigos")
    time.sleep(0.4)  # cortesia: evita sobrecarregar o servidor

total = len(articles)
print(f"\nTotal de artigos coletados: {total}")

# ---------------------------------------------------------------------------
# 4. Produção por autor (etapa intermediária do método)
# ---------------------------------------------------------------------------
prod = Counter(author for art in articles for author in art)
print(f"Total de autores distintos: {len(prod)}")
print("\nTop 15 autores mais produtivos:")
for i, (autor, n_art) in enumerate(prod.most_common(15), 1):
    print(f"  {i:2d}. {autor} — {n_art} artigo(s)")

# ---------------------------------------------------------------------------
# 5. Matriz de coautoria -> arestas do grafo
# ---------------------------------------------------------------------------
edge_weight = Counter()   # (a, b) -> nº de artigos em coautoria
for art in articles:
    art = sorted(set(art))          # sem repetição no mesmo artigo
    for i in range(len(art)):
        for j in range(i + 1, len(art)):
            a, b = art[i], art[j]
            edge_weight[(a, b)] += 1

print(f"\nArestas de coautoria: {len(edge_weight)}")

G = nx.Graph()
G.add_nodes_from(prod.keys())
for (a, b), w in edge_weight.items():
    G.add_edge(a, b, weight=w)

# Componentes (sub-redes desconectadas) e densidade
comps = list(nx.connected_components(G))
print(f"Componentes conexas: {len(comps)}")
print(f"Maior componente: {max(len(c) for c in comps)} autores")
print(f"Densidade da rede: {nx.density(G):.5f}")

# Graus (nº de coautores distintos de cada autor)
degree = dict(G.degree())
top_degree = sorted(degree.items(), key=lambda kv: kv[1], reverse=True)[:10]
print("\nTop 10 autores por número de coautores distintos (grau):")
for autor, d in top_degree:
    print(f"  {autor} — {d} coautores")

# ---------------------------------------------------------------------------
# 6. Visualização interativa (vis-network via CDN, análogo ao visNetwork)
# ---------------------------------------------------------------------------
nodes = [
    {
        "id": i,
        "label": autor,
        "value": prod[autor],                       # tamanho ~ nº de artigos
        "title": f"{autor}<br>Artigos: {prod[autor]}<br>Coautores: {degree[autor]}",
    }
    for i, autor in enumerate(sorted(prod))
]
name_to_id = {autor: i for i, autor in enumerate(sorted(prod))}
edges = [
    {"from": name_to_id[a], "to": name_to_id[b], "value": w}
    for (a, b), w in edge_weight.items()
]

html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>Rede de coautoria — REMat-SP</title>
<script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; }}
  header {{ padding: 16px 24px; border-bottom: 1px solid #ddd; }}
  header h1 {{ margin: 0 0 4px; font-size: 1.3rem; }}
  header p {{ margin: 0; color: #666; font-size: .9rem; }}
  #network {{ height: calc(100vh - 90px); }}
</style></head><body>
<header>
  <h1>Rede de coautoria — Revista de Educação Matemática (REMat-SP)</h1>
  <p>{total} artigos · {len(prod)} autores · {len(edge_weight)} laços de coautoria · {len(comps)} componentes</p>
</header>
<div id="network"></div>
<script>
const nodes = new vis.DataSet({json.dumps(nodes, ensure_ascii=False)});
const edges = new vis.DataSet({json.dumps(edges, ensure_ascii=False)});
const container = document.getElementById('network');
const data = {{ nodes: nodes, edges: edges }};
const options = {{
  nodes: {{ shape: 'dot', scaling: {{ min: 6, max: 40 }}, font: {{ size: 14 }} }},
  edges: {{ color: '#999', scaling: {{ min: 1, max: 6 }} }},
  physics: {{ barnesHut: {{ gravitationalConstant: -6000, springLength: 160, springConstant: 0.04 }} }},
  interaction: {{ hover: true, tooltipDelay: 100 }}
}};
new vis.Network(container, data, options);
</script></body></html>
"""

out = "/Users/gerlansilva/Downloads/remat_rede_coautoria.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"\nRede salva em: {out}")

# Salva também os dados brutos para reuso
data_out = {
    "artigos": articles,
    "producao_por_autor": dict(prod),
    "arestas": [{"a": a, "b": b, "peso": w} for (a, b), w in edge_weight.items()],
}
with open("/Users/gerlansilva/Downloads/remat_dados_coautoria.json", "w", encoding="utf-8") as f:
    json.dump(data_out, f, ensure_ascii=False, indent=2)
print("Dados brutos salvos em: /Users/gerlansilva/Downloads/remat_dados_coautoria.json")
