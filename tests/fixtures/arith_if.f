PROGRAM ARITHIF
       INTEGER X, Y
       X = -1
       IF (X) 10, 20, 30
  10   Y = 100
       GOTO 40
  20   Y = 200
       GOTO 40
  30   Y = 300
  40   CONTINUE
       PRINT *, 'Resultado IF aritmetico:', Y
       END
