import pandas as pd

def calcular_estatisticas():
    print("Calculando as estatísticas globais para a Média de LOC por método...")
    
    # Lê o CSV que contém os dados gerados anteriormente
    df = pd.read_csv('mean_loc_per_method_per_feature.csv')
    
    # Filtra apenas os registros onde a média é maior que zero.
    # Quando o valor é 0.0, significa que a feature ainda não existia ou não tinha código rastreado naquela release.
    # Incluir os 0.0 puxaria a média geral para baixo artificialmente.
    locs_validos = df[df['Mean LOC'] > 0]['Mean LOC']
    
    # Calcula as métricas estatísticas de todos os pontos de dados (todas as features em todas as releases)
    media_global = locs_validos.mean()
    desvio_padrao = locs_validos.std()
    minimo = locs_validos.min()
    maximo = locs_validos.max()
    
    print("\nResultados Estatísticos (Desconsiderando valores 0.0):")
    print(f"Total de amostras analisadas (feature/release): {len(locs_validos)}")
    print("-" * 40)
    print(f"Média Global:   {media_global:.2f} LOC/método")
    print(f"Desvio Padrão:  {desvio_padrao:.2f} LOC")
    print(f"Valor Mínimo:   {minimo:.2f} LOC/método")
    print(f"Valor Máximo:   {maximo:.2f} LOC/método")
    print("-" * 40)

if __name__ == "__main__":
    calcular_estatisticas()
