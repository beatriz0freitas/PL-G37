PROGRAM LOGWRITE
       LOGICAL A, B, C
       A = .TRUE.
       B = .FALSE.
       C = (A .AND. .NOT. B) .OR. (A .EQV. B)
       IF (C) THEN
          WRITE (6, *) 'Expressao logica verdadeira:', C
       ELSE
          WRITE (6, *) 'Expressao logica falsa:', C
       ENDIF
       END
