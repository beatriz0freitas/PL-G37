# Decisões do Projeto (PL-G37)

Este documento explica, em linguagem simples e objetiva, as decisões tomadas durante todo o desenvolvimento do compilador. O objetivo é clarificar escolhas que podem gerar dúvidas e mostrar os extras implementados.

## 1) Arquitetura geral e organização

### Pipeline por fases independentes
O compilador foi dividido em fases claras: Lexer → Parser/AST → Semântica → IR → Otimização → EWVM. Esta escolha permite testar cada parte isoladamente. Por exemplo, é possível correr apenas o lexer para validar tokens ou apenas a geração de IR para verificar tradução de controlo de fluxo. Além disso, cada fase recebe uma estrutura bem definida e devolve outra, o que reduz erros de acoplamento entre módulos.

**Porque não gerar EWVM diretamente da AST?**
Porque a IR intermedia isola a lógica da linguagem do backend. Isso torna as otimizações mais simples (trabalham sobre uma estrutura uniforme) e mantém o processo rastreável para depuração e testes.

### Organização por módulos
Cada fase tem a sua pasta própria (léxico, sintático, semântico, IR, otimização, codegen). Isto evita mistura de responsabilidades e facilita manutenção. Se for necessário alterar uma regra semântica, o impacto fica limitado ao módulo certo.

## 2) Formato Fortran 77 (fixed/free)

### Pré-processador antes do lexer
O Fortran 77 usa colunas fixas para comentários, labels e continuação. Em vez de complicar o lexer com regras de coluna, foi criado um pré-processador que “normaliza” o texto (identifica comentários, labels e continuações). O lexer fica assim focado apenas em reconhecer tokens.

**Porquê não tratar tudo no lexer?**
Porque ficaria muito frágil: pequenas variações de colunas ou comentários quebrariam regras regex. O pré-processador lida melhor com estas particularidades.

### Deteção automática de formato (`--format auto`)
Quando o formato não é especificado, o compilador tenta identificar o modo fixed/free. A heurística dá prioridade a padrões típicos de fixed-form (labels em colunas 1–5 e continuação na coluna 6). Também evita interpretar `!` e `&` dentro de strings como comentários/continuação, reduzindo falsos positivos.

## 3) Léxico

### Normalização para maiúsculas
Fortran 77 é case-insensitive. Por isso, todas as palavras-chave e identificadores são convertidos para maiúsculas. Isto evita duplicação de regras e garante comparação consistente.

### Labels como tokens próprios
Os labels numéricos são criados no pré-processamento e aparecem como tokens `LABEL`. Isto simplifica o parser e mantém a informação necessária para `GOTO` e `DO`. Sem isto, o parser teria de inferir labels a partir de posições de coluna, o que seria mais complexo.

### Lista de tokens antes do parser
O lexer produz uma lista completa de tokens antes de iniciar o parser. Esta decisão permite inserir tokens sintéticos (como `LABEL`) e facilita testes isolados da tokenização.

## 4) Sintaxe e AST

### Parser LALR(1) com PLY
Foi escolhida uma gramática LALR(1) porque permite lidar com precedência de operadores de forma clara e mantém a gramática legível. Isso evita implementar um parser manual recursivo com regras redundantes.

### Declarações antes das instruções
Na gramática, declarações aparecem antes de instruções executáveis. Isto segue a estrutura típica de F77 e simplifica a tabela de símbolos, pois todas as variáveis são conhecidas antes de começar a analisar as instruções.

### AST com `dataclasses`
Os nós da AST usam `dataclasses`, o que torna o código mais simples e autoexplicativo. Também facilita adicionar novos campos (ex.: `source_label`) sem criar classes complexas.

### Ambiguidade `ID(args)` resolvida na semântica
No Fortran, `F(X)` pode ser chamada de função ou acesso a array. O parser não tem informação suficiente para decidir. Por isso, cria sempre um nó `CallExpr`, e a análise semântica decide se é função, intrínseca ou array, consultando a tabela de símbolos.

### Labels preservadas em todas as instruções
Qualquer instrução pode ter `source_label`. Isto respeita o comportamento do Fortran 77, onde `GOTO` pode apontar para quase qualquer linha. Assim, não se perde a ligação com o código original.

## 5) Semântica e tabela de símbolos

### Tabelas de símbolos por escopo
Existe uma tabela para o programa principal e uma tabela para cada subprograma. Isto separa variáveis globais, parâmetros e locais. É essencial para distinguir variáveis com o mesmo nome em diferentes subprogramas.

### Validações aplicadas
A análise semântica verifica:
- declarações obrigatórias (exceto se tipagem implícita estiver ativa);
- uso antes de inicialização;
- compatibilidade de tipos em expressões e atribuições;
- índices de arrays (número e tipo);
- labels válidas para `GOTO` e `IF` aritmético;
- fecho correto de ciclos `DO` através de `CONTINUE` com label;
- aridade e tipo de chamadas a funções/subrotinas.

**Porque validar cedo?**
Para evitar que o backend receba casos ambíguos ou não suportados. Por exemplo, potências com expoentes reais seriam aceites no parser, mas a EWVM não suporta isso. A validação semântica dá erros mais claros ao utilizador.

### `IMPLICIT NONE` e `--implicit-typing`
O compilador suporta `IMPLICIT NONE` e também permite ativar tipagem implícita pela CLI. Isto mantém compatibilidade com Fortran 77, mas dá ao utilizador controlo explícito quando necessário.

### Conversões numéricas controladas
Conversões simples entre INTEGER/REAL/DOUBLE são permitidas e transformadas em instruções adequadas (`ITOF`, `FTOI`). Isso evita rejeitar programas realistas com expressões mistas.

### Limitação de potência
Apenas `INTEGER ** INTEGER` com expoente não negativo é aceite. Expoentes reais ou negativos são rejeitados por consistência com a EWVM.

## 6) Representação Intermédia (IR)

### IR em three-address code
A IR usa instruções simples com até três operandos. Isto torna o controlo de fluxo e as transformações mais diretas. Também permite comparar a saída antes e depois de otimizações.

### Visitor para geração de IR
Cada nó da AST tem um método específico de tradução. Isso evita grandes blocos de `if`/`isinstance` e facilita adicionar novos nós no futuro.

### Labels preservadas na IR
As labels numéricas são mantidas para garantir que `GOTO` e `DO` produzem saltos corretos. Isto também mantém rastreio claro entre o código fonte e a IR.

## 7) Otimizações

### Otimizar sobre IR (e não AST/EWVM)
A IR é uniforme e independente da máquina alvo, tornando as otimizações mais simples e seguras.

### Passes implementados (com explicação simples)
- **Constant folding:** calcula expressões constantes e substitui por literais.
- **Constant propagation:** substitui temporários conhecidos pelo seu valor literal.
- **Copy propagation:** elimina cadeias de cópias entre temporários.
- **CSE:** evita recalcular expressões iguais dentro do mesmo bloco.
- **Dead store elimination:** remove atribuições cujo valor nunca é lido.
- **Jump simplification:** elimina saltos redundantes ou condicionais triviais.
- **Dead code elimination:** remove blocos inalcançáveis.

### Ordem do pipeline
Os passes são aplicados várias vezes em sequência. A ideia é simples: um passo abre oportunidades para outro. Por exemplo, a propagação de constantes cria novas expressões que podem ser reduzidas pelo folding.

### Atributo relevante
Não se propagam constantes para variáveis do utilizador (apenas para temporários). Isto evita perder informação de tipo necessária no backend, como distinguir entre INTEGER e REAL ao emitir instruções EWVM.

## 8) Backend EWVM

### Compatibilidade estrita com a EWVM
O backend só gera instruções reais da EWVM. Instruções inexistentes (`NEG`, `NEQ`, `POW`) são substituídas por sequências equivalentes suportadas. Isto garante que o código final corre na VM fornecida.

### Potência inteira por multiplicação repetida
Como não existe `POW`, a potência inteira é implementada com um ciclo EWVM simples que multiplica o resultado pela base enquanto o expoente é positivo.

### Arrays como ponteiros
Arrays são alocados com `ALLOC` e acedidos com `PADD`, `LOAD` e `STORE`. Este modelo é o mais compatível com o que a EWVM oferece.

### Convenção de chamada com `FP`
Parâmetros ficam em offsets negativos do `FP` e o retorno em `0`. Isto cria um padrão de chamada estável entre subprogramas e facilita a geração de código consistente.

### Peephole no final
Após gerar o texto EWVM, aplica-se uma passagem peephole para remover padrões redundantes (por exemplo, sequências de `PUSH`/`POP` desnecessárias). O objetivo é limpar o resultado final sem alterar a semântica.

## 9) CLI e execução por fases

### `--stage` para isolar fases
Permite executar apenas uma fase, o que ajuda na depuração e na validação incremental. Por exemplo, se o parser está correto mas a IR está errada, é possível testar apenas o estágio `ir`.

### `--format auto|fixed|free`
Esta opção dá controlo total sobre o formato do ficheiro Fortran. O modo `auto` ajuda em casos em que o utilizador não sabe o formato do ficheiro.

## 10) Extras implementados (explicação simples)

1) **IR própria + otimizações avançadas**
Permite reduzir instruções e melhorar o desempenho final. Também torna o pipeline mais académico e verificável.

2) **Peephole no EWVM**
Limpa o código final removendo padrões redundantes, deixando a saída mais curta e fácil de comparar.

3) **Suporte a subprogramas (FUNCTION/SUBROUTINE)**
Permite definir e chamar funções/subrotinas com parâmetros, aproximando o compilador do Fortran real.

4) **Intrínsecas adicionais**
Funções como `MOD`, `INT`, `REAL`, `ABS`, `SQRT`, `MAX` e `MIN` são aceites diretamente, o que cobre muitos programas típicos.

5) **Compatibilidade com fixed e free form + deteção automática**
Aceita tanto ficheiros clássicos (fixed-form) como modernos (free-form) sem ajustes manuais.

## 11) Testes e validação

### Testes por componente + integração
Há testes dedicados para lexer, parser, semântica, IR, otimização, backend e CLI. Isto permite localizar erros com rapidez. Além disso, existem ficheiros EWVM esperados para validação textual e *fixtures* Fortran usados nos testes.

---

Se for necessário justificar uma decisão em detalhe, é possível apontar para o módulo correspondente em `src/` e para a explicação no relatório.
