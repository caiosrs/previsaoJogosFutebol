import pandas as pd
import requests

requisicao = requests.get("https://pt.wikipedia.org/wiki/Campeonato_Brasileiro_de_Futebol_de_2024_-_S%C3%A9rie_A")
tabelas = pd.read_html(requisicao.text)

tabela_classificacao = tabelas[6]
tabela_resultados = tabelas[7]
nomes_times = list(tabela_resultados["Casa \\ Fora"])
nomes_times_abreviados = list(tabela_resultados.columns)
nomes_times_abreviados.pop(0)

de_para_times = dict(zip(nomes_times_abreviados, nomes_times))
tabela_jogos_ajustada = tabela_resultados.set_index("Casa \\ Fora")
tabela_jogos_ajustada = tabela_jogos_ajustada.unstack().reset_index()
tabela_jogos_ajustada = tabela_jogos_ajustada.rename(columns={"level_0":"Fora", "Casa \\ Fora": "Casa", 0:"Resultado"})

def ajustar_apelido_time(linha):
    apelido = linha["Fora"]
    nome = de_para_times[apelido]
    return nome

tabela_jogos_ajustada["Fora"] = tabela_jogos_ajustada.apply(ajustar_apelido_time, axis=1)

tabela_jogos_ajustada = tabela_jogos_ajustada[tabela_jogos_ajustada["Fora"] != tabela_jogos_ajustada["Casa"] ]
tabela_jogos_ajustada["Resultado"] = tabela_jogos_ajustada["Resultado"].fillna("A jogar")

tabela_jogos_realizadas = tabela_jogos_ajustada[tabela_jogos_ajustada["Resultado"].str.contains("–")]
tabela_jogos_faltantes = tabela_jogos_ajustada[~tabela_jogos_ajustada["Resultado"].str.contains("–")]
tabela_jogos_faltantes = tabela_jogos_faltantes.drop(columns=["Resultado"])
tabela_jogos_realizadas[["gols_casa", "gols_fora"]] = tabela_jogos_realizadas["Resultado"].str.split("–", expand=True)
tabela_jogos_realizadas = tabela_jogos_realizadas.drop(columns=["Resultado"])
tabela_jogos_realizadas["gols_casa"] = tabela_jogos_realizadas["gols_casa"].astype(int)
tabela_jogos_realizadas["gols_fora"] = tabela_jogos_realizadas["gols_fora"].astype(int)
media_gols_dentro_casa = tabela_jogos_realizadas.groupby("Casa").mean(numeric_only=True)
media_gols_dentro_casa = media_gols_dentro_casa.rename(columns={"gols_casa":"Gols Feitos em Casa", "gols_fora":"Gols Sofridos em Casa"})
media_gols_fora_casa = tabela_jogos_realizadas.groupby("Fora").mean(numeric_only=True)
media_gols_fora_casa = media_gols_fora_casa.rename(columns={"gols_casa":"Gols Sofridos Feitos Fora", "gols_fora":"Gols Feitos Fora"})
tabela_estatisticas = media_gols_dentro_casa.merge(media_gols_fora_casa, left_index=True, right_index=True)
tabela_estatisticas = tabela_estatisticas.reset_index()
tabela_estatisticas = tabela_estatisticas.rename(columns={"Casa":"Time"})
from scipy.stats import poisson

def calcular_pontuacao_esperada(linha):
    time_casa = linha["Casa"]
    time_fora = linha["Fora"]

    lambda_casa = (tabela_estatisticas.loc[tabela_estatisticas["Time"]==time_casa, "Gols Feitos em Casa"].iloc[0]
                *
tabela_estatisticas.loc[tabela_estatisticas["Time"]==time_fora, "Gols Sofridos Feitos Fora"].iloc[0])

    lambda_fora = (tabela_estatisticas.loc[tabela_estatisticas["Time"]==time_fora, "Gols Feitos Fora"].iloc[0]
                    * tabela_estatisticas.loc[tabela_estatisticas["Time"]==time_casa, "Gols Sofridos em Casa"].iloc[0])

    pv_casa = 0
    p_empate = 0
    pv_fora = 0

    for gols_casa in range(8):
        for gols_fora in range(8):
            probabilidade_resultado = poisson.pmf(gols_casa, lambda_casa) * poisson.pmf(gols_fora, lambda_fora)
            if gols_casa == gols_fora:
                p_empate += probabilidade_resultado
            elif gols_casa > gols_fora:
                pv_casa += probabilidade_resultado
            elif gols_casa < gols_fora:
                pv_fora += probabilidade_resultado

    ve_casa = pv_casa * 3 + p_empate
    ve_fora = pv_fora * 3 + p_empate

    total = ve_casa + p_empate + ve_fora
    ve_casa /= total
    ve_fora /= total

    ve_casa = round(ve_casa * 100, 1)
    ve_fora = round(ve_fora * 100, 1)

    linha["Chance Casa Vencer"] = ve_casa
    linha["Chance Fora Vencer"] = ve_fora
    return linha
tabela_jogos_faltantes = tabela_jogos_faltantes.apply(calcular_pontuacao_esperada, axis=1)

import tkinter as tk
from tkinter import ttk

def exibir_tabela():
    root = tk.Tk()
    root.title("Tabela de Jogos Faltantes")

    # Criar uma Treeview (visualização em árvore) para exibir a tabela
    tree = ttk.Treeview(root)

    # Configurar as colunas da Treeview
    tree["columns"] = list(tabela_jogos_faltantes.columns)
    for column in tabela_jogos_faltantes.columns:
        tree.heading(column, text=column)
        tree.column(column, width=100, anchor="center")

    # Adicionar linhas da tabela
    for index, row in tabela_jogos_faltantes.iterrows():
        tree.insert("", "end", values=list(row))

    # Adicionar barra de rolagem
    scrollbar = ttk.Scrollbar(root, orient="vertical", command=tree.yview)
    scrollbar.pack(side="right", fill="y")
    tree.configure(yscrollcommand=scrollbar.set)

    tree.pack(expand=True, fill="both")

    root.mainloop()

# Chamar a função para exibir a tabela
exibir_tabela()