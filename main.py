# ==============================
# GOOGLE SHEETS
# ==============================

def carregar_produtos():
    try:
        url = "https://docs.google.com/spreadsheets/d/1speaE2hamb2j6yrKLMMOmo-k98FJZP7FG-_nBefVTDI/gviz/tq?tqx=out:json"
        response = requests.get(url)
        text = response.text

        json_data = json.loads(text.split("(", 1)[1].rstrip(");"))
        rows = json_data["table"]["rows"]

        produtos = []

        for r in rows:
            cells = r.get("c", [])

            nome = cells[0]["v"] if len(cells) > 0 and cells[0] else ""
            preco = cells[1]["v"] if len(cells) > 1 and cells[1] else ""
            link = cells[2]["v"] if len(cells) > 2 and cells[2] else ""
            plataforma = cells[3]["v"] if len(cells) > 3 and cells[3] else ""
            categoria = cells[4]["v"] if len(cells) > 4 and cells[4] else ""

            if nome and link:
                produtos.append({
                    "nome": nome,
                    "preco": preco,
                    "link": link,
                    "plataforma": plataforma,
                    "categoria": categoria
                })

        print(f"{len(produtos)} produtos carregados da planilha")
        return produtos

    except Exception as e:
        print("Erro ao carregar planilha:", e)
        return []