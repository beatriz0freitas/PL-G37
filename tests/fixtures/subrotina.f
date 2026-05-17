PROGRAM SUBCALL
       INTEGER A, B
       A = 7
       B = 5
       CALL MOSTRA(A, B)
       END
       SUBROUTINE MOSTRA(X, Y)
       INTEGER X, Y, S
       S = X + Y
       WRITE (6, *) 'Soma por subrotina:', S
       RETURN
       END
