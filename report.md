# Compilador Fortran 77 para EWVM

**Processamento de Linguagens - G37**
Ana Beatriz Freitas (a106853) | Luis Miguel Coelho (a106843) | Matilde Teixeira
**Ano letivo:** 2026

---

## 1\. Introdução

O presente relatório descreve o trabalho desenvolvido no âmbito da unidade curricular de Processamento de Linguagens. O objetivo deste projeto foi o desenvolvimento de um compilador para um subconjunto prático de Fortran 77 *standard*, alinhado com os requisitos do enunciado, capaz de reconhecer os programas e construções suportados, validar a sua estrutura sintática e coerência semântica, e traduzir o código fonte para instruções executáveis na máquina virtual EWVM disponibilizada na unidade curricular.

A solução foi implementada em Python com recurso às ferramentas `ply.lex` e `ply.yacc`, seguindo uma arquitetura modular inspirada nas fases clássicas de compilação. O projeto encontra-se organizado em componentes independentes, responsáveis pelas diferentes etapas do processo de compilação, o que facilita a manutenção, os testes e a extensão futura do compilador.

Foram também implementadas funcionalidades de valorização, incluindo criação da representação intermédia, otimizações de código, suporte a subprogramas e compatibilidade com diferentes formatos de Fortran.

---

## 2. Arquitetura Geral

O projeto foi organizado por fases independentes numa *pipeline* clássica de compilação, explicitando a passagem por IR antes da geração de código. Cada fase recebe uma estrutura bem definida e produz a estrutura consumida pela fase seguinte, o que facilita testes isolados, simplifica depuração e evita que a lógica de uma fase se misture com outra.

```text
Fortran 77 -> Lexer -> Parser/AST -> Semântica -> IR -> Otimização -> EWVM
```

A implementação separa claramente o pré-processamento de formato, o *lexer*, o *parser*/AST, a análise semântica, a geração de IR, a otimização e o *backend* EWVM, com uma CLI que permite executar cada estágio de forma independente. Esta modularidade permite observar e validar cada fase, bem como justificar decisões técnicas como a resolução semântica da ambiguidade entre chamadas e acessos a *arrays* e a existência de uma IR própria para facilitar otimização e testes.

---

## 3. Análise Léxica

A análise léxica foi implementada com `ply.lex`. Antes do *lexer*, existe uma fase de pré-processamento em `processor.py`, uma vez que o Fortran 77 tem regras de formato que não são convenientes de tratar diretamente com expressões regulares do *lexer*.

No modo *fixed-form*, o pré-processador interpreta a coluna 1 como possível comentário (`C`, `c`, `*`, `!`), as colunas 1–5 como zona de *label*, a coluna 6 como continuação e as colunas 7–72 como zona de código. Foi ainda acrescentada tolerância para ficheiros menos rígidos, usados frequentemente em editores modernos.

No modo *free-form*, são suportados comentários com `!` e continuação com `&`. Quando o formato é `auto`, a deteção heurística ignora ocorrências de `!` e `&` dentro de *strings* e comentários para reduzir falsos positivos, privilegiando padrões típicos de *fixed-form* (*labels* em colunas 1–5 e continuação na coluna 6) antes de concluir por *free-form*.

O *lexer* reconhece palavras-chave (`PROGRAM`, `INTEGER`, `REAL`, `IF`, `DO`, `GOTO`, etc.), identificadores, inteiros, reais, lógicos, strings, operadores aritméticos, operadores relacionais pontuados (`.EQ.`, `.LE.`, etc.), operadores lógicos (`.AND.`, `.OR.`, `.NOT.`) e pontuação. Como Fortran é *case-insensitive*, identificadores e palavras-chave são normalizados para maiúsculas.

Optamos por tratar os *labels* no pré-processamento e inseri-los como *tokens* próprios. Isto simplifica o *parser* e preserva a informação necessária para `GOTO` e `DO`.

Outra decisão foi tokenizar previamente a lista de *tokens* antes de iniciar o *parser*, em vez de usar um *stream* direto do *lexer*. Esta abordagem facilita a injeção de *tokens* sintéticos como `LABEL`, mantém a separação entre pré-processamento e sintaxe, e permite testar a tokenização de forma isolada.

---

## 4. Análise Sintática e AST

A análise sintática foi implementada com `ply.yacc`, usando uma gramática LALR(1). Esta escolha é adequada para expressões com precedência e associatividade, e evita reescrever a gramática em estilo recursivo descendente manual.

A opção por LALR(1) permite manter a recursividade esquerda natural nas expressões e usar uma tabela explícita de precedências, mantendo a gramática legível e alinhada com a especificação ANSI F77. Foi também decidido separar `decl_list` de `stmt_list`, impondo que declarações aparecem antes de instruções executáveis, o que simplifica a construção da tabela de símbolos na análise semântica.

A AST é definida com `dataclasses`, o que permite representar o programa de forma clara e tipada. Existem nós para programa principal, subprogramas, declarações, instruções e expressões. As *labels* de origem são preservadas nas instruções para permitir validação semântica e geração correta de saltos.

O subconjunto sintático suportado cobre `PROGRAM ... END`, declarações de tipos (`INTEGER`, `REAL`, `LOGICAL`, `CHARACTER`, `DOUBLE PRECISION`), *arrays* com dimensões constantes, atribuições escalares e a *arrays*, expressões aritméticas/relacionais/lógicas e concatenação, `IF ... THEN ... ELSEIF ... ELSE ... ENDIF`, `IF` aritmético, `DO label var = start, end [, step]`, `GOTO`, `CONTINUE`, `STOP`, `RETURN`, operações de E/S (`READ`, `PRINT`, `WRITE`), chamadas `CALL` e subprogramas externos `FUNCTION`/`SUBROUTINE`.

A distinção entre `A(I)` como acesso a array e `F(I)` como chamada de função não é resolvida no *parser*. O *parser* cria inicialmente uma forma ambígua (`CallExpr`) e a análise semântica decide se se trata de *array*, função definida ou intrínseca.

Para suportar *labels* numéricos, qualquer instrução pode receber um *label* através de um atributo único, o que mantém a correspondência com o código fonte e evita fases adicionais de resolução. Esta decisão preserva o comportamento típico de Fortran 77, onde praticamente qualquer instrução pode ser destino de um `GOTO`.

---

## 5. Gramática Utilizada

A gramática implementada cobre o subconjunto de Fortran 77 definido no enunciado, organizada em quatro módulos de produção PLY. A forma resumida é:

```
program        -> PROGRAM ID body END subprogram_list
body           -> decl_list stmt_list
decl           -> type_spec var_decl_list | IMPLICIT NONE
type_spec      -> INTEGER | REAL | LOGICAL | CHARACTER | DOUBLE PRECISION
stmt           -> LABEL unlabeled_stmt | unlabeled_stmt
unlabeled_stmt -> assign | if_stmt | do_stmt | goto | continue |
                  print | read | write | call | stop | return
if_stmt        -> IF (expr) THEN stmt_list elseif_chain ENDIF
               | IF (expr) INT_LIT , INT_LIT , INT_LIT
elseif_chain   -> ELSEIF (expr) THEN stmt_list elseif_chain | ELSE stmt_list | ε
do_stmt        -> DO INT_LIT ID = expr , expr [, expr]
expr           -> expr op expr | op expr | (expr) | literal | ID | ID(arg_list)
subprogram     -> type_spec FUNCTION ID (params) body END
               | SUBROUTINE ID [(params)] body END
```

De destacar que qualquer instrução pode ter um `LABEL` prefixado, não apenas `CONTINUE`, ficando esse valor guardado como atributo `source_label` no nó AST para resolução correcta de `GOTO` e `DO` nas fases seguintes. Também a forma `ID(args)` é sempre produzida como `CallExpr` pelo parser logo a distinção entre acesso a *array* e chamada de função é resolvida pela análise semântica consultando a tabela de símbolos.

A tabela de precedências segue a ordem esperada para Fortran, isto é, equivalência lógica, `OR`, `AND`, `NOT`, relacionais, concatenação, soma/subtração, multiplicação/divisão, unários e potência. O operador `**` é reconhecido, mas o subconjunto suportado é limitado a `INTEGER ** INTEGER`.

---

## 6. Análise Semântica

A análise semântica percorre a AST, constrói tabelas de símbolos e anota nós com informação de tipo. Existe uma tabela para o programa principal e uma tabela própria para cada subprograma.

As validações cobrem declaração obrigatória de variáveis, deteção de duplicados, uso antes de inicialização, distinção entre escalares e *arrays*, número e tipo de índices de *arrays*, coerência de tipos em expressões e atribuições, existência de labels para `GOTO` e `IF` aritmético, terminação correta de ciclos `DO` em `CONTINUE` com a *label* correspondente, aridade de funções e subrotinas, separação entre função e subrotina, e suporte a intrínsecas como `MOD`, `INT`, `REAL`, `FLOAT`, `ABS`, `SQRT`, `MAX` e `MIN`. O analisador também reconhece `IMPLICIT NONE` (desativa tipagem implícita quando presente) e suporta tipagem implícita opcional via CLI (`--implicit-typing`), seguindo a regra F77 (I–N → `INTEGER`, restantes → `REAL`).

As conversões numéricas simples entre `INTEGER`, `REAL` e `DOUBLE PRECISION` são permitidas na semântica e concretizadas no *backend* com instruções como `ITOF` e `FTOI`.

Os expoentes negativos literais, expoentes reais e potências reais são rejeitados semanticamente, para evitar que um programa válido nas fases iniciais falhe apenas no *backend*. Isto deve-se ao não suporte a operações com expoente por parte da máquina virtual disponibilizada.

---

## 7. Representação Intermédia

A IR adoptada é de estilo *Three-Address Code*, ou seja, cada instrução tem no máximo um operador e três operandos. Esta escolha em vez de gerar EWVM directamente da AST isola a semântica do *backend*, simplifica o teste por fases e permite aplicar otimizações antes da emissão final.

Exemplos de instruções IR:

```text
t1 = A + B
IF t1 GOTO THEN1 ELSE GOTO ENDIF1
GOTO L10
PRINT X, "texto"
```

O gerador de IR usa uma abordagem de *visitor*: cada nó relevante da AST tem um método de tradução próprio. O gerador cobre atribuições, *arrays*, expressões, `IF`, `IF` aritmético, `DO`, `GOTO`, I/O, chamadas e subprogramas.

A opção por um *visitor* com despacho dinâmico mantém o gerador extensível e evita cadeias longas de `isinstance`, o que simplifica a evolução do compilador sem alterar a estrutura das fases anteriores.

As *labels* numéricas de Fortran são mapeadas para labels internas, preservando a ligação com `GOTO` e com o fecho de ciclos `DO`. Para ciclos, é usada uma pilha de contextos que permite fechar corretamente o corpo quando é encontrado o `CONTINUE` correspondente.

A opção de manter uma IR explícita de três endereços, em vez de gerar EWVM diretamente a partir da AST, permitiu isolar a semântica do *backend*, simplificar a validação por fases e aplicar otimizações locais antes da emissão final de código, mantendo a tradução rastreável e testável.

Outra decisão relevante foi preservar *labels* ao longo das fases intermédias em vez de reestruturar o controlo de fluxo de imediato. Esta escolha mantém a correspondência com o código fonte e reduz ambiguidades na geração de saltos para `GOTO`, `IF` aritmético e terminação de ciclos `DO`.

---

## 8. Otimização

A fase de otimização atua sobre a representação intermédia (IR), antes da geração de código EWVM. Esta posição no *pipeline* é intencional uma vez que a IR em três endereços é uma estrutura uniforme e independente do alvo, o que torna as transformações mais simples de implementar, testar e raciocinar do que se fossem feitas diretamente sobre a AST ou sobre o texto EWVM.

As otimizações estão organizadas em passes independentes, cada uma com uma única responsabilidade. O módulo `src/optimizer.py` expõe a função pública `optimize(instructions)` que aplica a pipeline completa.

#### 8.1 Passes implementados

##### A) *Constant Folding*

Avalia em tempo de compilação operações binárias (`IROp`) e unárias (`IRUnaryOp`) cujos dois operandos sejam literais conhecidos. Quando possível, substitui a instrução por uma `IRAssign` com o valor calculado.

Exemplos de transformações:

```text
t1 = 3 + 4      →   t1 = 7
t2 = 10 / 2     →   t2 = 5
t3 = .NOT. 0    →   t3 = 1
t4 = 2 < 5      →   t4 = 1
```

A divisão por zero não é avaliada estaticamente logo a instrução original é preservada para que o erro ocorra em *runtime*, tal como o *standard* exige.

##### B) *Constant Propagation*

Propaga literais atribuídos a temporários para os seus usos subsequentes, substituindo referências a `tN` pelo valor literal. A análise é feita por *data-flow* sobre a CFG (*Control Flow Graph*), usando uma função de transferência por bloco e uma operação de *meet* (interseção) nos pontos de junção.

```text
t1 = 42
t2 = t1 + 1     →   t2 = 42 + 1
```

A propagação é conservadora em relação a variáveis de utilizador (identificadores nomeados como `X`, `N`, etc.) logo estas não são substituídas por literais mesmo quando o valor é conhecido, para preservar a informação de tipo necessária ao backend EWVM, por exemplo, distinguir `PUSHG` de `STOREG` entre uma variável `REAL` e uma `INTEGER`.

Adicionalmente, o ambiente de constantes é limpo nos pontos de `IRProcBegin` (início de novo escopo) e invalidado por `IRRead`, que sobrescreve variáveis em *runtime*.

##### C) *Copy Propagation*

Propaga cópias diretas entre temporários, substituindo usos de `tN` por `tM` quando existe uma atribuição `tN = tM` ativa. Percorre linearmente os blocos e invalida o ambiente nos limites de bloco (labels, início/fim de subprogramas).

```text
t2 = t1
t3 = t2 + 1     →   t3 = t1 + 1
```

##### D) *Common Subexpression Elimination* - CSE

Dentro de cada bloco básico, deteta operações binárias e unárias com os mesmos operandos que já foram calculadas anteriormente. Quando encontra uma repetição, substitui a instrução redundante por uma cópia do temporário que já contém o resultado.

```text
t1 = A + B
t2 = A + B      →   t2 = t1
```

Operadores comutativos (`+`, `*`, `==`, `AND`, etc.) são normalizados antes de comparar, pelo que `A + B` e `B + A` são reconhecidos como a mesma expressão. O mapa de expressões conhecidas é invalidado nos limites de bloco (*labels*) e quando um temporário é redefinido.

##### E) D*ead Store Elimination*

Remove atribuições a temporários cujo valor nunca é lido. A análise usa liveness global sobre a CFG, isto é, para cada bloco calcula-se o conjunto de temporários vivos à saída, `live-out`, usando a equação clássica de *backwards* *data-flow*. Uma definição é eliminada se o temporário definido não está vivo após essa instrução.

```text
t1 = 1        ← eliminado (t1 nunca é lido)
t2 = X + Y
PRINT t2
```

Apenas instruções sem efeitos colaterais (`IRAssign`, `IROp`, `IRUnaryOp`, `IRLoadArray`) são candidatas à eliminação. Chamadas (`IRCall`) e operações de I/O nunca são removidas, mesmo que o destino não seja usado.

##### F) *Jump Simplification* 

Simplifica padrões redundantes de saltos antes da eliminação de código morto:

* **JUMP para o label seguinte:** `JUMP L1` imediatamente antes de `L1:` é removido.
* ***Conditional jump* com constante:** `IF 0 GOTO T ELSE F` converte-se em `GOTO F`; analogamente para condição verdadeira.
* ***Conditional jump* com ambos os ramos iguais:** `IF cond GOTO L ELSE L` converte-se em `GOTO L`.

##### G) *Dead Code Elimination* - DCE

Remove blocos básicos inalcançáveis calculando os blocos alcançáveis a partir dos pontos de entrada, isto é, programa principal e cada subprograma, por travessia da CFG. Blocos não alcançáveis são descartados na serialização final. Marcadores estruturais (`IRProcBegin`, `IRProcEnd`) são sempre preservados, independentemente da alcançabilidade, para garantir que o *backend* recebe informação de escopo completa.

#### 8.2 *Pipeline* e ordem de aplicação

Os passes são aplicados em sequência fixa pelo `optimizer.py`:

```text
constant_propagation
    → constant_folding
        → copy_propagation
            → common_subexpression_elimination
                → constant_propagation
                    → constant_folding
                        → copy_propagation
                            → constant_propagation
                                → dead_store_elimination
                                    → jump_simplification
                                        → dead_code_elimination
```

A ordem não é arbitrária. *Constant propagation* e *folding* são alternados porque cada passe pode criar novas oportunidades para o outro, isto é, a propagação substitui temporários por literais, e o *folding* colapsa operações com literais em novas atribuições que, por sua vez, podem ser propagadas novamente. A *copy propagation* encurta cadeias de cópias antes de novas passagens. O *dead store elimination* e o *jump simplification* preparam a IR para o DCE final, que descarta os blocos entretanto tornados inalcançáveis.

#### 8.3 Documentação do código

Além do relatório, o projeto inclui *docstrings Python* nas classes e funções principais de todos os módulos. As *docstrings* documentam responsabilidades, parâmetros, valores devolvidos e erros esperados de cada componente. Esta opção torna o código mais fácil de compreender sem necessidade de ler a implementação completa, e permite gerar documentação técnica estruturada com ferramentas Python standard como `pydoc` ou `pdoc`.

---

## 9. Geração de Código EWVM

O *backend* traduz a IR para instruções da EWVM. A memória global é reservada antes de `START` com valores iniciais, e variáveis globais são acedidas com `PUSHG` e `STOREG`. Os *arrays* são alocados com `ALLOC`, guardados como ponteiros e acedidos com `PADD`, `LOAD` e `STORE`.

As operações inteiras usam `ADD`, `SUB`, `MUL`, `DIV`, `MOD` e comparadores inteiros. Operações reais usam `FADD`, `FSUB`, `FMUL`, `FDIV` e comparadores reais. O *backend* emite conversões `ITOF`, `FTOI` e `ATOF` quando necessário.

Como a EWVM documentada não fornece `NEG`, `NEQ` ou `POW`, estas operações são traduzidas para sequências existentes, concretamente a negação aritmética é implementada como `0 - valor`, a operação de diferente é gerada com `EQUAL` seguido de `NOT` e a potência inteira é obtida por multiplicação repetida num ciclo EWVM.

Para `INTEGER ** INTEGER`, o *backend* usa auxiliares internos para base, expoente e resultado. O resultado começa em `1`, enquanto o expoente for maior que zero, multiplica-se o resultado pela base e decrementa-se o expoente. Este suporte é intencionalmente limitado a expoentes inteiros não negativos.

Os subprogramas externos são emitidos como *labels* próprios. A convenção de chamada usa `PUSHA` e `CALL`, com *frames* baseadas em `FP`: parâmetros ficam em *offsets* negativos, o *slot* de retorno em `0`, e variáveis locais/temporários em offsets positivos. Após a geração, é aplicada uma passagem *peephole* sobre o texto EWVM para remover padrões redundantes e estabilizar o código final.

No *backend*, evitou-se introduzir pseudo-instruções inexistentes na EWVM, traduzindo operações ausentes como `NEG`, `NEQ` e `POW` em sequências equivalentes suportadas pela máquina. Esta decisão mantém a geração estritamente compatível com o conjunto de instruções disponível.

---

## 10. Dificuldades

Uma das dificuldades a destacar foi o formato histórico de Fortran 77. O tratamento de colunas, labels e continuações podia tornar o *lexer* difícil de manter. A solução foi criar um pré-processador separado, deixando o *lexer* responsável apenas por reconhecer *tokens*.

Uma outra dificuldade foi o controlo de fluxo baseado em *labels*. Em vez de transformar tudo em blocos estruturados logo no *parser*, as *labels* foram preservadas na AST e resolvidas depois. Esta decisão manteve a correspondência com o código original e simplificou a validação de `GOTO` e `DO`.

Outra dificuldade foi a ambiguidade de `ID(...)`. Em Fortran, a mesma forma pode significar chamada de função ou acesso a *array*. A opção escolhida foi resolver isso semanticamente, quando já existe uma tabela de símbolos.

---

## 11. Testes e Validação

A validação é feita com `pytest`, cobrindo cada fase e casos de integração. Existem *fixtures* Fortran em `tests/fixtures/` e ficheiros EWVM esperados em `tests/expected_vm/`.

Atualmente a suíte inclui 263 testes distribuídos por léxico (103), sintático (26), semântico (16), IR (11), geração EWVM (23), CLI (9), otimização de IR (49) e *peephole* (26). A geração EWVM é validada por comparação textual com saídas esperadas e por testes específicos para *arrays*, intrínsecas, subprogramas, conversões, potência inteira e compatibilidade com instruções reais da EWVM.

---

## 12. Instruções de Execução

Requisitos: o projeto assume Python 3.11+, `ply>=3.11`, `pytest` para desenvolvimento/testes e `make` como utilitário recomendado.

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

A execução final na EWVM do docente pode ser feita copiando o conteúdo gerado para a interface web da VM e comparando o *output* esperado. O guia em [README.md](README.md) descreve em maior detalhe como correr todo o projeto.

---

## 13. Conclusão

O projeto apresenta uma *pipeline* completa de compilação para um subconjunto de Fortran 77. A solução usa PLY, valida semanticamente o programa, gera IR, aplica otimizações e produz código EWVM.

A separação por módulos, a preservação de *labels*, a resolução semântica de ambiguidades e a validação automatizada tornam a solução adequada para demonstração e evolução. Os exemplos principais do enunciado são suportados, há código VM esperado no repositório e a suíte atual confirma o comportamento implementado.
