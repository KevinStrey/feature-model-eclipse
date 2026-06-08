# Relatório de Features Não Mapeadas (NOT FOUND)

Abaixo está a lista consolidada das features cujas versões não puderam ser resolvidas em commits pelo nosso script em nenhuma das heurísticas (ou que sofreram timeout no Git).

Estes itens geralmente ocorreram por um dos motivos:
- **Ausência total no histórico:** O componente não marcou de forma alguma a string da versão (nem no manifesto, nem via *timestamp*, nem via *tags*).
- **Timeout no Pickaxe:** Versões soltas sem timestamps (ex: `ECLIPSELINK 3.10.0`) em repositórios gigantes, onde buscar em toda a árvore do Git levaria dezenas de minutos por requisição e por segurança o script limitou a 30s.

## Lista de Ocorrências (Por Release)

| Release | Componente | Versão |
| :--- | :--- | :--- |
| **2018-09** | SCOUT | 8.0.0 |
| **2018-09** | WEBTOOLS | 3.11.0 |
| **2018-12** | DATATOOLS | 1.14.103 |
| **2018-12** | SCOUT | 8.0.0 |
| **2018-12** | WEBTOOLS | 3.12.0 |
| **2019-03** | DATATOOLS | 1.14.104 |
| **2019-03** | SCOUT | 9.0.0 |
| **2019-06** | DATATOOLS | 1.14.105 |
| **2019-06** | SCOUT | 9.0.0 |
| **2019-09** | DATATOOLS | 1.14.105 |
| **2019-09** | SCOUT | 9.0.0 |
| **2019-09** | WEBTOOLS | 3.15.0 |
| **2019-12** | DATATOOLS | 1.14.105 |
| **2019-12** | ECLIPSELINK | 3.16.0 |
| **2019-12** | SCOUT | 9.0.0 |
| **2019-12** | WEBTOOLS | 3.16.0 |
| **2020-03** | DATATOOLS | 1.14.105 |
| **2020-03** | ECLIPSELINK | 3.17.0 |
| **2020-03** | WEBTOOLS | 3.17.0 |
| **2020-06** | DATATOOLS | 1.14.105 |
| **2020-06** | ECLIPSELINK | 3.18.0 |
| **2020-09** | DATATOOLS | 1.14.200 |
| **2020-09** | ECLIPSELINK | 3.19.0 |
| **2020-12** | DATATOOLS | 1.14.200 |
| **2020-12** | ECLIPSELINK | 3.20.0 |
| **2020-12** | WEBTOOLS | 3.20.0 |
| **2021-03** | DATATOOLS | 1.14.200 |
| **2021-03** | ECLIPSELINK | 3.21.0 |
| **2021-06** | DATATOOLS | 1.14.200 |
| **2021-06** | ECLIPSELINK | 3.22.0 |
| **2021-09** | DATATOOLS | 1.14.200 |
| **2021-09** | ECLIPSELINK | 3.23.0 |
| **2021-12** | DATATOOLS | 1.14.202 |
| **2021-12** | ECLIPSELINK | 3.24.0 |
| **2022-03** | ECLIPSELINK | 3.25.0 |
| **2022-03** | SCOUT | 12.0.1 |
| **2022-06** | ECLIPSELINK | 3.26.0 |
| **2022-06** | SCOUT | 12.0.15 |
| **2022-09** | ECLIPSELINK | 3.27.0 |
| **2022-09** | SCOUT | 12.0.29 |
| **2022-12** | ECLIPSELINK | 3.28.0 |
| **2022-12** | SCOUT | 12.0.41 |
| **2023-03** | ECLIPSELINK | 3.29.0 |
| **2023-03** | SCOUT | 13.0.6 |
| **2023-06** | ECLIPSELINK | 3.30.0 |
| **2023-06** | MYLYN | 5.22.1 |
| **2023-06** | SCOUT | 13.0.19 |
| **2023-09** | ECLIPSELINK | 3.31.0 |
| **2023-09** | SCOUT | 13.0.22 |
| **2023-12** | ECLIPSELINK | 3.32.0 |
| **2023-12** | SCOUT | 13.0.27 |
| **2024-03** | DATATOOLS | 1.16.1 |
| **2024-03** | ECLIPSELINK | 3.33.0 |
| **2024-03** | SCOUT | 13.0.31 |
| **2024-06** | DATATOOLS | 1.16.1 |
| **2024-06** | ECLIPSELINK | 3.34.0 |
| **2024-06** | SCOUT | 13.0.36 |
| **2024-09** | DATATOOLS | 1.16.1 |
| **2024-09** | ECLIPSELINK | 3.35.0 |
| **2024-09** | SCOUT | 13.0.41 |
| **2024-12** | DATATOOLS | 1.16.1 |
| **2024-12** | ECLIPSELINK | 3.36.0 |
| **2024-12** | SCOUT | 13.0.46 |
| **2025-03** | DATATOOLS | 1.16.3 |
| **2025-03** | ECLIPSELINK | 3.37.0 |
| **2025-03** | SCOUT | 14.0.1 |
| **2025-06** | DATATOOLS | 1.16.3 |
| **2025-06** | ECLIPSELINK | 3.38.0 |
| **2025-06** | SCOUT | 14.0.5 |
| **2025-09** | DATATOOLS | 1.16.3 |
| **2025-09** | ECLIPSELINK | 3.39.0 |
| **2025-09** | SCOUT | 14.0.15 |
| **2025-12** | DATATOOLS | 1.16.3 |
| **2025-12** | ECLIPSELINK | 3.40.0 |
| **2025-12** | SCOUT | 14.0.23 |
| **2026-03** | DATATOOLS | 1.16.3 |
| **2026-03** | ECLIPSELINK | 3.41.0 |
| **2026-03** | SCOUT | 14.0.29 |
| **JunoSR1** | WEBTOOLS | 3.4.1 |
| **Mars.1** | ECLIPSELINK | 3.7 |
| **Neon.1** | WINDOWBUILDER | 4.6 |
| **Neon.1a** | ECLIPSELINK | 3.7 |
| **Neon.2** | WINDOWBUILDER | 4.6 |
| **Neon.3** | WINDOWBUILDER | 4.6 |
| **Neon.3_respin** | ECLIPSELINK | 3.7 |
| **Oxygen.1a** | ECLIPSELINK | 3.7 |
| **Oxygen.1a_respin** | ECLIPSELINK | 3.7 |
| **Oxygen.2** | ECLIPSELINK | 3.9.2 |
| **Oxygen.2** | WEBTOOLS | 3.9.2 |
| **Oxygen.2_respin** | ECLIPSELINK | 3.9.2 |
| **Oxygen.2_respin** | WEBTOOLS | 3.9.2 |
| **Oxygen.3** | ECLIPSELINK | 3.9.3 |
| **Oxygen.3** | WEBTOOLS | 3.9.3 |
| **Photon.0** | SCOUT | 8.0.0 |
| **PhotonM7** | SCOUT | 8.0.0 |
| **PhotonRC4** | SCOUT | 8.0.0 |
