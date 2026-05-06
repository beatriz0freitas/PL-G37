# Compilador Fortran 77 para EWVM

**Processamento de Linguagens - G37**  
Ana Beatriz Freitas (a106853) | Luis Miguel Coelho (a106843) | Matilde Teixeira  
**Instituição:** Universidade do Minho  
**Ano letivo:** 2026

---

## 1\. Introdução

Este relatório descreve a implementação de um compilador para a linguagem Fortran 77, desenvolvido em Python com PLY. O compilador lê programas `.f`, valida-os léxica, sintática e semanticamente, gera uma representação intermédia, aplica otimizações simples e traduz o resultado para código da EWVM.

O objetivo principal foi construir uma solução modular, testável e alinhada com o enunciado da UC. Assim, a implementação segue uma pipeline clássica de compilação:

text

Copy

text

Copy

```text
Fortran 77 -> Lexer -> Parser/AST -> Semântica -> IR -> Otimização -> EWVM
```

O projeto cobre os requisitos essenciais: declarações, expressões aritméticas/lógicas/relacionais, `IF`, `DO` com labels, `GOTO`, `READ`, `PRINT`, geração de VM e testes. Como valorização, inclui representação intermédia, otimização local e suporte a `FUNCTION`/`SUBROUTINE`.

## 2\. Arquitetura Geral

A arquitetura foi organizada por fases independentes. Cada fase recebe uma estrutura bem definida e produz a estrutura consumida pela fase seguinte. Esta escolha facilita testes isolados, simplifica depuração e evita que a lógica de uma fase se misture com outra.

Estrutura principal:

AQUI PODEMOS METER UM GRÁFICO DA PINTA COM O FLUXO DO PROJETO, COM ARQUITETURA

## 3\. Análise Léxica

A análise léxica foi implementada com `ply.lex`, como pedido no enunciado. Antes do lexer, existe uma fase de pré-processamento em `processor.py`, porque o Fortran 77 tem regras de formato que não são convenientes de tratar diretamente com expressões regulares do lexer.

No modo *fixed-form*, o pré-processador interpreta:

-   coluna 1 como possível comentário (`C`, `c`, `*`, `!`);
-   colunas 1-5 como zona de label;
-   coluna 6 como continuação;
-   colunas 7-72 como zona de código.

Também foi adicionada tolerância para ficheiros menos rígidos, usados frequentemente em editores modernos. No modo *free-form*, são suportados comentários com `!` e continuação com `&`.

O lexer reconhece palavras-chave (`PROGRAM`, `INTEGER`, `REAL`, `IF`, `DO`, `GOTO`, etc.), identificadores, inteiros, reais, lógicos, strings, operadores aritméticos, operadores relacionais pontuados (`.EQ.`, `.LE.`, etc.), operadores lógicos (`.AND.`, `.OR.`, `.NOT.`) e pontuação. Como Fortran é case-insensitive, identificadores e palavras-chave são normalizados para maiúsculas.

Optamos por tratadar os labels no pré-processamento e inseri-los como tokens próprios. Isto simplifica o parser e preserva a informação necessária para `GOTO` e `DO`.

## 4\. Análise Sintática e AST

A análise sintática foi implementada com `ply.yacc`, usando uma gramática LALR(1). Esta escolha é adequada para expressões com precedência e associatividade, e evita reescrever a gramática em estilo recursivo descendente manual.

A AST é definida com `dataclasses`, o que permite representar o programa de forma clara e tipada. Existem nós para programa principal, subprogramas, declarações, instruções e expressões. As labels de origem são preservadas nas instruções para permitir validação semântica e geração correta de saltos.

Construções sintáticas suportadas:

-   `PROGRAM ... END`;
-   declarações `INTEGER`, `REAL`, `LOGICAL`, `CHARACTER`, `DOUBLE PRECISION`;
-   arrays declarados com dimensões constantes;
-   atribuições escalares e a arrays;
-   expressões aritméticas, relacionais, lógicas e concatenação;
-   `IF ... THEN ... ELSEIF ... ELSE ... ENDIF`;
-   `IF` aritmético;
-   `DO label var = start, end [, step]`;
-   `GOTO`, `CONTINUE`, `STOP`, `RETURN`;
-   `READ`, `PRINT`, `WRITE`;
-   `CALL`;
-   `FUNCTION` e `SUBROUTINE` externos.

A distinção entre `A(I)` como acesso a array e `F(I)` como chamada de função não é resolvida no parser. O parser cria inicialmente uma forma ambígua (`CallExpr`) e a análise semântica decide se se trata de array, função definida ou intrínseca.

## 5\. Gramática Utilizada

A gramática implementada cobre o subconjunto prático do projeto. A forma resumida é:

METER QUALQUER CENA

A tabela de precedências segue a ordem esperada para Fortran: equivalência lógica, `OR`, `AND`, `NOT`, relacionais, concatenação, soma/subtração, multiplicação/divisão, unários e potência. O operador `**` é reconhecido, mas o subconjunto suportado é apenas `INTEGER ** INTEGER`.

## 6\. Análise Semântica

A análise semântica percorre a AST, constrói tabelas de símbolos e anota nós com informação de tipo. Existe uma tabela para o programa principal e uma tabela própria para cada subprograma.

Validações implementadas:

-   declaração obrigatória de variáveis;
-   deteção de declarações duplicadas;
-   uso antes de inicialização;
-   distinção entre escalares e arrays;
-   número correto de índices em arrays;
-   índices de arrays do tipo `INTEGER`;
-   tipos em expressões e atribuições;
-   labels existentes para `GOTO` e `IF` aritmético;
-   `DO` terminado por `CONTINUE` com a label correta;
-   aridade de funções e subrotinas;
-   separação entre função e subrotina;
-   suporte a intrínsecas como `MOD`, `INT`, `REAL`, `FLOAT`, `ABS`, `SQRT`, `MAX` e `MIN`.

As conversões numéricas simples entre `INTEGER`, `REAL` e `DOUBLE PRECISION` são permitidas na semântica e concretizadas no backend com instruções como `ITOF` e `FTOI`.

Para `**`, foi tomada uma decisão conservadora. Apenas `INTEGER ** INTEGER` é aceite. Os expoentes negativos literais, expoentes reais e potências reais são rejeitados semanticamente, para evitar que um programa válido nas fases iniciais falhe apenas no backend. Isto deve-se ao não suporte a operações com expoente por parte da máquina virtual disponibilizada.

## 7\. Representação Intermédia

A IR é uma representação de três endereços, com temporários, labels e instruções tipadas. A escolha de uma IR explícita, o 3 adress code, em vez de gerar diretamente EWVM a partir da AST, facilita depuração, testes e otimização.

Exemplos de instruções IR:


```text
t1 = A + BIF t1 GOTO THEN1 ELSE GOTO ENDIF1GOTO L10PRINT X, "texto"
```

O gerador de IR usa uma abordagem de visitor: cada nó relevante da AST tem um método de tradução próprio. O gerador cobre atribuições, arrays, expressões, `IF`, `IF` aritmético, `DO`, `GOTO`, I/O, chamadas e subprogramas.

As labels numéricas de Fortran são mapeadas para labels internas, preservando a ligação com `GOTO` e com o fecho de ciclos `DO`. Para ciclos, é usada uma pilha de contextos que permite fechar corretamente o corpo quando é encontrado o `CONTINUE` correspondente.

## 8\. Otimização

A valorização é feita sobre a IR, antes da geração de EWVM. Foram implementadas três otimizações locais:

-   **Constant propagation:** substitui temporários por literais conhecidos.
-   **Constant folding:** calcula expressões constantes em tempo de compilação.
-   **Dead code elimination:** remove instruções inalcançáveis após `JUMP`, `STOP` ou `RETURN`.

A ordem aplicada é:


```text
propagation -> folding -> propagation -> folding -> propagation -> DCE
```

Esta sequência cobre cadeias curtas de temporários, mantendo a implementação simples e previsível. A otimização preserva variáveis de utilizador para não perder informação necessária ao backend.

## 9\. Geração de Código EWVM

O backend traduz a IR para instruções da EWVM. A memória global é reservada antes de `START` com valores iniciais, e variáveis globais são acedidas com `PUSHG` e `STOREG`. Os arrays são alocados com `ALLOC`, guardados como ponteiros e acedidos com `PADD`, `LOAD` e `STORE`.

As operações inteiras usam `ADD`, `SUB`, `MUL`, `DIV`, `MOD` e comparadores inteiros. Operações reais usam `FADD`, `FSUB`, `FMUL`, `FDIV` e comparadores reais. O backend emite conversões `ITOF`, `FTOI` e `ATOF` quando necessário.

Como a EWVM documentada não fornece `NEG`, `NEQ` ou `POW`, estas operações são traduzidas para sequências existentes:

-   negação aritmética: `0 - valor`;
-   diferente: `EQUAL` seguido de `NOT`;
-   potência inteira: multiplicação repetida num ciclo EWVM.

Para `INTEGER ** INTEGER`, o backend usa auxiliares internos para base, expoente e resultado. O resultado começa em `1`, enquanto o expoente for maior que zero, multiplica-se o resultado pela base e decrementa-se o expoente. Este suporte é intencionalmente limitado a expoentes inteiros não negativos.

Os subprogramas externos são emitidos como labels próprios. A convenção de chamada usa `PUSHA` e `CALL`, com frames baseadas em `FP`: parâmetros ficam em offsets negativos, o slot de retorno em `0`, e variáveis locais/temporários em offsets positivos.

## 10\. Dificuldades e Decisões de Projeto

A primeira dificuldade foi o formato histórico de Fortran 77. O tratamento de colunas, labels e continuações podia tornar o lexer difícil de manter. A solução foi criar um pré-processador separado, deixando o lexer responsável apenas por reconhecer tokens.

A segunda dificuldade foi o controlo de fluxo baseado em labels. Em vez de transformar tudo em blocos estruturados logo no parser, as labels foram preservadas na AST e resolvidas depois. Esta decisão manteve a correspondência com o código original e simplificou a validação de `GOTO` e `DO`.

Outra dificuldade foi a ambiguidade de `ID(...)`. Em Fortran, a mesma forma pode significar chamada de função ou acesso a array. A opção escolhida foi resolver isso semanticamente, quando já existe uma tabela de símbolos.

No backend, a principal decisão foi não inventar pseudo-instruções da EWVM. Sempre que a VM não fornece uma operação diretamente, o compilador emite uma sequência equivalente com instruções existentes. Isto acontece, por exemplo, com `NEG`, `NEQ` e `**` inteiro.

## 11\. Testes e Validação

A validação é feita com `pytest`, cobrindo cada fase e casos de integração. Existem fixtures Fortran em `tests/fixtures/` e ficheiros EWVM esperados em `tests/expected_vm/`.

Estado atual da suíte:

| Componente | Testes |
| --- | --- |
| Léxico | 102 |
| Sintático | 25 |
| Semântico | 16 |
| IR | 9 |
| Codegen EWVM | 21 |
| CLI | 9 |
| Otimizador | 29 |
| **Total** | **211** |

A geração EWVM é validada por comparação textual com saídas esperadas e por testes específicos para arrays, intrínsecas, subprogramas, conversões, potência inteira e compatibilidade com instruções reais da EWVM.

## 12\. Instruções de Execução

Requisitos:

-   Python 3.11+ conforme configurado no projeto;
-   `ply>=3.11`;
-   `pytest` para desenvolvimento/testes;
-   `make` opcional, mas recomendado.

Instalação recomendada:


```bash
make setup
```


Gerar um ficheiro `.vm`:


```bash
python3 -m src --stage codegen --format free tests/fixtures/hello.f > hello.vm
```

Executar testes:


```bash
make test
```

ou:


```bash
python3 -m pytest
```

A execução final na EWVM do docente pode ser feita copiando o conteúdo gerado para a interface web da VM e comparando o output esperado.

## 13\. Limitações e Trabalho Futuro

O compilador implementa um subconjunto significativo, mas não todo o standard Fortran 77. Limitações conhecidas:

-   sem `IMPLICIT NONE` efetivo;
-   sem implicit typing de variáveis não declaradas;
-   potência limitada a `INTEGER ** INTEGER` com expoente não negativo;
-   sem potência real ou expoentes negativos;
-   passagem de argumentos por referência ainda não é completa;
-   sem execução automática contra a VM remota;
-   otimizações globais avançadas não foram implementadas.

Como trabalho futuro, faria sentido melhorar a convenção de chamada por referência, automatizar a execução EWVM, suportar implicit typing opcional, ampliar a cobertura de formatos Fortran e acrescentar otimizações globais como eliminação de subexpressões comuns.

## 14\. Conclusão

O projeto apresenta uma pipeline completa de compilação para um subconjunto de Fortran 77. A solução usa PLY nas fases obrigatórias, valida semanticamente o programa, gera IR, aplica otimizações e produz código EWVM.

A separação por módulos, a preservação de labels, a resolução semântica de ambiguidades e a validação automatizada tornam a solução adequada para demonstração e evolução. Os exemplos principais do enunciado são suportados, há código VM esperado no repositório e a suíte atual confirma o comportamento implementado.