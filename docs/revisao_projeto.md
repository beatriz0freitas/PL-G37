# Revisão detalhada — Enunciado vs Implementação

> Projeto PL 2026 (Fortran 77 → EWVM)
> Data: 2026-05-15

## 1) Conformidade com o enunciado

**Requisitos mínimos (enunciado):**
- **Lexer com PLY (ply.lex):** cumprido (src/analise_lexica/lexer.py + preprocessors).
- **Parser com PLY (ply.yacc):** cumprido (src/analise_sintatica/parser.py).
- **Semântica:** verificação de tipos, labels e coerência básica (src/analise_semantica/analyzer.py).
- **Tradução para VM:** cumprido via IR + codegen EWVM (src/representacao_intermedia + src/codegen).
- **Otimização local (valorização):** cumprido (src/optimizer.py).
- **Testes:** cumprido (tests/*).

**Valorização:**
- **IR explícita** + **otimização**: cumprido.
- **Subprogramas** (FUNCTION/SUBROUTINE): cumprido.

**Formato fonte:**
- O enunciado deixa ao grupo escolher fixed-form ou free-form. Aqui há suporte aos **dois**, com heurística “auto”. Isto é um **ponto forte** a destacar.

---

## 2) Correções necessárias (prioridade alta)

### 2.1. Relatório tem placeholders e inconsistências
O relatório atual contém texto provisório e secções incompletas:
- “AQUI PODEMOS METER UM GRÁFICO...”, “METER QUALQUER CENA”, e excertos duplicados.
- Secção de gramática “forma resumida” está ausente.
- Existem blocos de “text Copy”/duplicações no início.

**Ação:** limpar e completar o relatório com: diagrama de arquitetura, gramática resumida, descrição do IR e exemplos. 

### 2.2. Contagem de testes inconsistente
- Em docs/Estado.md: **208/208**.
- Em report.md: **211**.

**Ação:** reconciliar contagens, atualizar tabela para refletir o estado real do repositório.

### 2.3. Deteção de formato em CLI pode falhar
A heurística em cli.py marca “free” se encontrar “&” em qualquer linha. Isto pode ocorrer em strings ou comentários, causando deteção incorreta.

**Ação:** considerar um detetor mais robusto (ex.: ignorar strings e comentários, ou depender do preprocessador com fallback), e documentar a heurística no relatório.

---

## 3) Melhorias recomendadas (funcionais e de qualidade)

### 3.1. Semântica e conformidade Fortran 77
- **IMPLICIT NONE:** token existe mas a semântica não aplica a regra. Sugere-se implementar (ou documentar claramente a ausência).
- **Implicit typing opcional:** Fortran 77 permite inferência por inicial do identificador. Poderia ser opcional com flag.
- **Passagem por referência:** está referida como incompleta no relatório. Definir e implementar uma convenção clara (p. ex. sempre por referência) para alignar com F77.

### 3.2. Qualidade de diagnóstico de erros
- Incluir **snippet** de código e sublinhado em mensagens de erro.
- **Recuperação de erros no parser** para reportar múltiplos problemas num único run.

### 3.3. Cobertura e documentação
- Incluir no relatório um quadro explícito: “o que é suportado / o que não é”.
- Adicionar testes para:
  - potenciação com expoente 0
  - ciclos DO com STEP negativo
  - IF aritmético em conjunto com GOTO
  - chamadas a funções intrínsecas em expressões complexas

---

## 4) Otimizações que acrescentam valor

### 4.1. IR-level (alto valor, baixo risco)
- **Copy propagation** (propagar temporários que são cópias diretas).
- **Common subexpression elimination** em blocos simples.
- **Dead store elimination** (atribuições nunca usadas).
- **Simplificação de saltos** (JUMP para o próximo label; ifs com constantes).

### 4.2. CFG básico e otimizações por bloco
- Construir **basic blocks** e um **CFG leve**.
- Aplicar **constant propagation global** (não apenas linear).
- **DCE** mais precisa (com análise de liveness).

### 4.3. Peephole no EWVM
- Eliminar sequências redundantes (ex.: PUSHI 0 + ADD, STORE imediato seguido de LOAD sem uso).
- Compactar sequências de conversões ITOF/FTOI redundantes.

---

## 5) Pontos fulcrais a mencionar no relatório

### 5.1. Conformidade com o enunciado
- Lexer e Parser com PLY.
- Suporte de **fixed-form** e **free-form** (decisão de projeto).
- Pipeline: AST → IR → otimização → EWVM.
- Subprogramas (FUNCTION/SUBROUTINE) para valorização.

### 5.2. Decisões técnicas
- Separação em fases independentes e testáveis.
- Pré-processamento para tratar colunas/continuações em fixed-form.
- Resolução semântica da ambiguidade **CallExpr vs ArrayRef**.
- Estratégia para `**` (potência) e para operadores ausentes na EWVM.

### 5.3. Backend EWVM
- Layout de memória global, arrays como ponteiros, frames com FP.
- Convenção de chamadas e registo do retorno.
- Conversões numéricas e suporte às intrínsecas.

### 5.4. Testes
- Número de testes por fase (lex, parse, sem, IR, codegen, optimizer, CLI).
- Exemplo de validação manual na EWVM (processo real exigido pela UC).

### 5.5. Limitações
- Implicit typing / IMPLICIT NONE.
- Potência restrita a INTEGER ** INTEGER.
- Passagem por referência ainda parcial.
- Sem integração automática com EWVM remota.

---

## 6) Checklist de ações imediatas

1. **Completar e limpar report.md** (diagramas, gramática, remover placeholders).
2. **Reconciliar contagem de testes** entre Estado.md e report.md.
3. **Documentar limitações explícitas** com tabela “suportado / não suportado”.
4. **Reforçar testes** para casos fronteira (DO com STEP negativo, potenciação, IF aritmético).
5. **Planear 1–2 otimizações extra** (copy propagation + peephole simples) para valorização.

---

## 7) Observações finais
O projeto cumpre os requisitos essenciais e já tem uma arquitetura sólida. A prioridade agora é melhorar o relatório (qualidade e consistência) e reforçar o alinhamento com o enunciado, destacando a robustez do pipeline e as decisões técnicas.
