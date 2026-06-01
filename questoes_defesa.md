# Questões de Defesa — Compilador Fortran 77 (PL-G37)

Abaixo estão perguntas possíveis para a defesa, organizadas por tema. Cada aluno deve ser capaz de responder com exemplos do próprio código.

## 1) Arquitetura geral
1. Qual é a pipeline completa do compilador e o que entra/sai em cada fase?
2. Por que razão usaram uma IR antes da geração de EWVM?
3. O que ganham com a separação por módulos?
4. Qual foi a decisão mais importante a nível de arquitetura?

## 2) Léxico e formatos
5. Como distinguem fixed-form de free-form no modo `auto`?
6. Porque criaram um pré-processador em vez de fazer tudo no lexer?
7. Como tratam labels no fixed-form?
8. O Fortran é case-insensitive. Onde tratam isso?

## 3) Parser e AST
9. Porque escolheram LALR(1) com PLY e não um parser manual?
10. Que precedência e associatividade definiram para operadores?
11. Como garantem que declarações aparecem antes das instruções?
12. Como representam a AST e porquê `dataclasses`?
13. Como lidam com labels na AST?

## 4) Semântica
14. Como constroem e usam a tabela de símbolos?
15. Como resolvem a ambiguidade `ID(args)` (função vs array)?
16. Que verificações semânticas são feitas?
17. O que acontece com `IMPLICIT NONE`?
18. Como suportam tipagem implícita via CLI?
19. Que conversões de tipos são permitidas?
20. Porque não permitem potência com expoentes reais ou negativos?

## 5) IR
21. O que é a IR de three-address code no vosso projeto?
22. Como traduzem estruturas de controlo (`IF`, `DO`, `GOTO`) para IR?
23. Como preservam labels ao longo das fases?
24. Porque usar visitor/dynamic dispatch no gerador de IR?

## 6) Otimizações
25. Quais os passes implementados e a ordem do pipeline?
26. Por que razão alternam constant propagation e folding?
27. O que é CSE e onde é aplicada?
28. Em que casos a eliminação de stores é segura?
29. Como garantem que não removem efeitos laterais?

## 7) Backend EWVM
30. Porque não inventaram instruções ausentes (`NEG`, `NEQ`, `POW`)?
31. Como geram potência inteira sem `POW`?
32. Como são geridos arrays na EWVM?
33. Qual é a convenção de chamada usada (FP, offsets)?
34. Onde e porquê aplicam peephole?

## 8) Testes e validação
35. Que tipos de testes têm e o que validam?
36. Como testam a geração de EWVM?
37. Existe validação manual? Quando é necessária?

## 9) Extras e limitações
38. Que extras implementaram e porquê?
39. Que funcionalidades ficaram fora do subconjunto?
40. Se tivessem mais tempo, o que melhorariam?

---

**Sugestão:** treinar respostas com exemplos concretos dos ficheiros em `tests/fixtures/` e saídas em `tests/expected_vm/`.
