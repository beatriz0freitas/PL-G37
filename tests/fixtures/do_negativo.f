PROGRAM DONEG
       INTEGER I, SOMA
       SOMA = 0
       DO 50 I = 10, 2, -2
          SOMA = SOMA + I
  50   CONTINUE
       PRINT *, 'Soma decrescente:', SOMA
       END
