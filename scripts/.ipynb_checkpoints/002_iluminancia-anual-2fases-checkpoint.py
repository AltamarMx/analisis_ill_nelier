# Script para ejecutar la simulacion de dos fases para cada una de las aulas evaluadas. Asegurarse de haber ejecutado previamente "start", para tener los directorios necesarios para almacenar los resultados.

import os
os.system('gendaymtx -m 4 ../modelo/Cue.wea > ../modelo/matrices/anual.smx')
aulas = ["A10-1","A10-2","A20-1","A20-2","A40-1","A40-2"]
aulas = ["A40-1","A40-2"]
for aula in aulas:
    os.system("rfluxmtx < ../modelo/objects/{}.pts -I+ -v -ab 10 -ad 65536 -dj 1 -dp 1 -dt 0 -dc 1 -as 2048 -lw 1e-6 -n 6 - ../modelo/skies/dc_sky_noground.rad ../modelo/materiales.rad ../modelo/{}.rad > ../modelo/matrices/dc_day.mtx".format(aula,aula))
    # os.system("dctimestep ../modelo/matrices/dc_day.mtx ../modelo/matrices/anual.smx | rmtxop -fa -c 47.7 119.9 11  - > ../resultados/iluminancia/{}_anual.ill".format(aula))
