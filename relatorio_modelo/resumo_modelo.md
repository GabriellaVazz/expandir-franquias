# Resumo do Modelo — Score de Potencial de Expansão

## Modelo selecionado
**Random Forest**

## Métricas de avaliação
- ROC-AUC (teste): 0.7714
- Acurácia (teste): 0.7500
- ROC-AUC (validação cruzada 5-fold): 0.8867

## Base de dados
- Franquias coletadas: 48 (Portal do Franchising / ABF)
- Features utilizadas: 11
- Variável-alvo: sucesso binário (acima da mediana do segmento = 1)

## Variáveis mais importantes
1. Número de unidades
2. Tempo de mercado (anos)
3. Investimento inicial (log)
4. Segmento de atuação
5. PIB per capita

## Distribuição do score
- Média: 57.6
- Mediana: 76.0
- Score Muito Alto (>80): 23 franquias
- Score Alto (60–80): 6 franquias
- Score Moderado (40–60): 1 franquias
- Score Baixo (<40): 18 franquias

## Nota sobre a variável-alvo
A variável-alvo foi definida como sucesso binário: uma franquia é considerada
bem-sucedida se seu número de unidades por ano de operação está acima da mediana
do seu segmento. Esta definição usa crescimento relativo como proxy de sucesso,
compensando parcialmente o viés de sobrevivência dos dados públicos da ABF.
Os dados de mortalidade empresarial do SEBRAE foram incorporados como feature
adicional para calibrar o modelo em relação às taxas históricas de encerramento
por segmento.
