PROGRAM INTRINS
       INTEGER I, J, K
       REAL R, S, T
       I = 3
       J = 7
       R = ABS(-4.0)
       S = SQRT(9.0)
       K = MAX(I, 2) + MIN(J, 5)
       T = FLOAT(K) / 2.0
       PRINT *, 'Resultados:', R, S, K, T
       END
