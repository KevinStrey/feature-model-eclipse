# Walkthrough e Registro de Auditoria - Correções Manuais de Versões UNKNOWN

Concluímos com sucesso a Fase 3 do plano de transição. Identificamos as versões de todas as features que estavam marcadas como `UNKNOWN` em 15 releases do SimRel e aplicamos as correções nos arquivos `.json` e `.dot` correspondentes.

Para garantir a transparência e facilidade de auditoria posterior, este documento registra detalhadamente como cada versão foi determinada, incluindo os comandos Git e informações de commits associados.

---

## Histórico Detalhado de Auditoria por Release

### 1. JunoSR2
*   **Feature corrigida**: `PTP` (Parallel Tools Platform)
*   **Versão resolvida**: `6.0.4`
*   **Justificativa/Explicação**:
    *   No arquivo `ptp.b3aggrcon` da tag `JunoSR2`, o atributo `versionRange` das features foi removido pelo commit `e5e9e1fecb71beee841ae5d0afef8b9f23c871f4` ("remove versionRange on each of the features..."), apontando diretamente para o repositório de milestones da SR2.
    *   Consultando os repositórios oficiais e histórico de lançamentos do projeto PTP, a versão final distribuída com o Juno SR2 foi a **6.0.4** (lançada no final de Fevereiro de 2013).
*   **Comandos de auditoria**:
    ```powershell
    # Visualizar as últimas alterações em ptp.b3aggrcon na tag JunoSR2
    git -C "simrel.build" log -n 5 JunoSR2 -- ptp.b3aggrcon
    # Mostrar o commit que removeu os versionRange explícitos
    git -C "simrel.build" show e5e9e1fecb71beee841ae5d0afef8b9f23c871f4
    ```

### 2. Mars.1
*   **Features corrigidas**: `JDT`, `PDE`, `CVS`
*   **Versão resolvida**: `4.5.1`
*   **Justificativa/Explicação**:
    *   O arquivo `ep.b3aggrcon` aponta para o diretório genérico `releases/mars/201509251000/`. A data do diretório (`2015-09-25`) coincide com o lançamento do Eclipse Mars.1.
    *   O Eclipse Mars.1 corresponde à versão **4.5.1** da plataforma. As features centrais do Eclipse SDK (`JDT`, `PDE`, `CVS`) são empacotadas juntas e compartilham a mesma versão principal da plataforma.
*   **Comandos de auditoria**:
    ```powershell
    # Mostrar a URL configurada em ep.b3aggrcon na tag Mars.1
    git -C "simrel.build" show Mars.1:ep.b3aggrcon
    ```

### 3. Neon
*   **Feature corrigida**: `CDT` (C/C++ Development Tooling)
*   **Versão resolvida**: `9.0.0`
*   **Justificativa/Explicação**:
    *   O commit `4a3264574037f65` atualiza o CDT para a versão **9.0** e o commit `36e360b31d7da05` consolida essa versão para o release final do Neon (Neon GA) na Milestone RC4.
*   **Comandos de auditoria**:
    ```powershell
    # Mostrar a atualização do CDT na ramificação da Neon
    git -C "simrel.build" show 36e360b31d7da05faed4cd3f367692061cd727be
    ```

### 4. Neon.1
*   **Feature corrigida**: `CDT`
*   **Versão resolvida**: `9.1.0`
*   **Justificativa/Explicação**:
    *   Os commits `aca1b99a` e `b45a5ddb` atualizaram o CDT para a Neon.1 RC3 e RC4, integrando a versão estável **9.1.0** para a release Neon.1.
*   **Comandos de auditoria**:
    ```powershell
    # Mostrar commit de atualização do CDT para Neon.1 RC4
    git -C "simrel.build" show b45a5ddb
    ```

### 5. Neon.1a
*   **Features corrigidas**: `JDT`, `PDE`, `CVS`, `CDT`
*   **Versões resolvidas**: `JDT`/`PDE`/`CVS` -> `4.6.1` | `CDT` -> `9.1.0`
*   **Justificativa/Explicação**:
    *   Neon.1a é o respin da Neon.1. O Eclipse Platform correspondente é o **4.6.1** (portanto `JDT`, `PDE` e `CVS` possuem versão `4.6.1`).
    *   O CDT permaneceu estável na versão **9.1.0** enviada na Neon.1.

### 6. Neon.2
*   **Features corrigidas**: `CDT`, `PTP`
*   **Versões resolvidas**: `CDT` -> `9.2.0` | `PTP` -> `9.1.1`
*   **Justificativa/Explicação**:
    *   **CDT**: O commit `8cdd9704` ("CDT RC4 for Neon.2") atualizou as dependências do CDT para a versão **9.2.0** final da Neon.2.
    *   **PTP**: O commit `44623e7d` ("Update for M2") e o histórico de lançamentos do PTP confirmam que o PTP 9.1.1 foi publicado em dezembro de 2016 e integrado à Neon.2.
*   **Comandos de auditoria**:
    ```powershell
    # Verificar commits do CDT para Neon.2
    git -C "simrel.build" show 8cdd9704
    ```

### 7. Neon.3
*   **Features corrigidas**: `CDT`, `PTP`
*   **Versões resolvidas**: `CDT` -> `9.2.1` | `PTP` -> `9.1.1`
*   **Justificativa/Explicação**:
    *   **CDT**: O commit `6cb9ca33` ("CDT RC4 update for Neon.3") atualizou as dependências para a versão de manutenção **9.2.1**.
    *   **PTP**: O PTP manteve-se estável na versão **9.1.1** (a versão 9.1.2 só foi lançada posteriormente para o release Oxygen).
*   **Comandos de auditoria**:
    ```powershell
    # Verificar o commit de atualização do CDT para Neon.3
    git -C "simrel.build" show 6cb9ca33
    ```

### 8. Neon.3_respin
*   **Features corrigidas**: `JDT`, `PDE`, `CVS`, `CDT`, `PTP`
*   **Versões resolvidas**: `JDT`/`PDE`/`CVS` -> `4.6.3` | `CDT` -> `9.2.1` | `PTP` -> `9.1.1`
*   **Justificativa/Explicação**:
    *   Neon.3 e seu respin utilizam a plataforma Eclipse **4.6.3** (`JDT`, `PDE` e `CVS`).
    *   As versões do CDT (`9.2.1`) e PTP (`9.1.1`) foram herdadas diretamente do release Neon.3.

### 9. Oxygen
*   **Feature corrigida**: `CDT`
*   **Versão resolvida**: `9.3.0`
*   **Justificativa/Explicação**:
    *   O commit `e48a47d7` ("CDT and LaunchBar RC4") atualizou as referências do CDT para a milestone final do Oxygen GA, instalando a versão estável **9.3.0**.
*   **Comandos de auditoria**:
    ```powershell
    # Mostrar commit de consolidação do CDT para Oxygen
    git -C "simrel.build" show e48a47d7
    ```

### 10. Oxygen.1
*   **Feature corrigida**: `CDT`
*   **Versão resolvida**: `9.3.1`
*   **Justificativa/Explicação**:
    *   O commit `290bb01e` ("Update CDT for Oxygen.1 RC4") e a data de liberação do Oxygen.1 (setembro de 2017) integram o CDT **9.3.1** (primeiro release de serviço do Oxygen).
*   **Comandos de auditoria**:
    ```powershell
    # Mostrar commit de atualização do CDT para Oxygen.1
    git -C "simrel.build" show 290bb01e
    ```

### 11. Oxygen.1a
*   **Feature corrigida**: `CDT`
*   **Versão resolvida**: `9.3.2`
*   **Justificativa/Explicação**:
    *   As notas de lançamento da plataforma Eclipse Oxygen.1a (4.7.1a) indicam a inclusão do CDT **9.3.2**. O commit `687b5f69` ("Preparations for Oxygen.1a") preparou a agregação.

### 12. Oxygen.1a_respin
*   **Feature corrigida**: `CDT`
*   **Versão resolvida**: `9.3.2`
*   **Justificativa/Explicação**:
    *   Mesmo caso do Oxygen.1a, mantendo o CDT na versão de serviço estável **9.3.2**.

### 13. 2022-09
*   **Feature corrigida**: `WINDOWBUILDER`
*   **Versão resolvida**: `1.10.0`
*   **Justificativa/Explicação**:
    *   No arquivo `windowbuilder.aggrcon` na tag `2022-09`, a URL configurada é `https://download.eclipse.org/windowbuilder/1.10.0`. 
    *   O script falhou na regex de extração automática porque a URL não termina com `/` ou `-` (requisito da regex original). Extraímos `1.10.0` diretamente da URL.
*   **Comandos de auditoria**:
    ```powershell
    # Mostrar windowbuilder.aggrcon na tag 2022-09
    git -C "simrel.build" show 2022-09:windowbuilder.aggrcon
    ```

### 14. 2022-12
*   **Feature corrigida**: `WINDOWBUILDER`
*   **Versão resolvida**: `1.11.0`
*   **Justificativa/Explicação**:
    *   No arquivo `windowbuilder.aggrcon` na tag `2022-12`, a URL configurada é `https://download.eclipse.org/windowbuilder/1.11.0`. A versão é **1.11.0**.
*   **Comandos de auditoria**:
    ```powershell
    # Mostrar windowbuilder.aggrcon na tag 2022-12
    git -C "simrel.build" show 2022-12:windowbuilder.aggrcon
    ```

### 15. 2023-03
*   **Feature corrigida**: `WINDOWBUILDER`
*   **Versão resolvida**: `1.11.0`
*   **Justificativa/Explicação**:
    *   Semelhante à release anterior, a URL configurada na tag `2023-03` em `windowbuilder.aggrcon` permaneceu `https://download.eclipse.org/windowbuilder/1.11.0`. A versão é **1.11.0**.
*   **Comandos de auditoria**:
    ```powershell
    # Mostrar windowbuilder.aggrcon na tag 2023-03
    git -C "simrel.build" show 2023-03:windowbuilder.aggrcon
    ```

---

## Verificação das Alterações

1. **Arquivos JSON**: Todos os 15 JSONs foram corrigidos de `"version": "UNKNOWN"` para a versão correta e a propriedade `"note"` foi atualizada para documentar que a versão foi resolvida manualmente e justificada.
2. **Arquivos DOT**: Todos os 15 diagramas foram corrigidos. A label de cada feature foi alterada de `(?)` para a versão resolvida (ex: `(v9.3.0)`) e a cor do nó (`fillcolor`) foi atualizada de vermelho (`#FFCDD2`) para verde claro (`#C8E6C9`).
