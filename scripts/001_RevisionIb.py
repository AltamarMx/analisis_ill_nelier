# Script para generar im'agenes hdr en aulas, dias criticos 22 y 12 de diciembre, 22 y 12 de noviembre, 20 de junio, 5 de junio y 29 de mayo.
import os
import pandas as pd

wea = pd.read_csv('../modelo/Cue.wea', header =None, skiprows=range(0,6),sep=" ") # Lectura de archivo wea para crear descripcion de cielo de acuerdo con fecha y hora
wea.columns=['mes','dia','hora','dir','dif']

def revision_Ib(aula, dia, hora, ab = 0): # Función para crear imagen HDR para determinada aula, dia, hora y ambient bounces ab
    options = '-ab {} -ad 2000 -dj 1 -dp 1 -dt 0 -dc 1 -as 500 -lw 1e-2 -n 32 -x 1000 -y 1000'.format(ab) # opciones de rtpict
    posicion = (dia-1)*24+hora-1
    vista = aula
    if 'A40' in aula: # Para el aula 40 tenemos dos vistas, una hacia el norte y una hacia el sur
        if dia < 200: # Si el d'ia es menor a 200, utilizaremos la vista hacia el norte
            vista = aula + 'N'
        elif dia >= 200: # Si el d'ia es mayor a 200, utilizaremos la vista hacia el sur
            vista = aula + 'S'
    cielo = open('../modelo/skies/cielo.rad', 'w') # Generamos archivo para descripcion de cielo
    cielo.write('!gendaylit {} {} +{} -a 18.835 -W {} {} \n'.format(wea.mes.iloc[posicion],wea.dia.iloc[posicion],wea.hora.iloc[posicion],wea.dir.iloc[posicion],wea.dif.iloc[posicion]))
    cielo.write('\n skyfunc glow skydome \n 0 \n 0 \n 4 1 1 1 0 \n')
    cielo.write('\n skydome source sky \n 0 \n 0 \n 4 0 0 1 180 \n')
    cielo.write('\n skydome source grnd \n 0 \n 0 \n 4 0 0 -1 180 \n')
    cielo.close()
    os.system('oconv ../modelo/skies/cielo.rad ../modelo/{}.rad > ../modelo/octrees/aula.oct'.format(aula)) # Generamos octree
    os.system('rm ambfile.amb') # Eliminamos archivo con valores ambientales creado en simulaciones previas
    os.system('rtpict {} -vf ../modelo/views/{}.vf -af ambfile.amb ../modelo/octrees/aula.oct > ../resultados/revision_Ib/foto/{}_{}-{}-ab{}.hdr'.format(options,vista,vista,dia,hora,ab)) # generamos imagen
    os.system('rtpict {} -vf ../modelo/views/{}.vf -af ambfile.amb ../modelo/octrees/aula.oct > ../resultados/revision_Ib/foto/{}_{}-{}-ab{}.hdr'.format(options,vista,vista,dia,hora,ab)) # repetimos orden para imagen con mejor apariencia

def revision_glare(aula,dia,hora,ab=10): # funcion para evaluar glare en imagenes generadas
    vista = aula
    if 'A40' in aula: # Para el aula 40 tenemos dos vistas, una hacia el norte y una hacia el sur
        if dia < 200: # Si el d'ia es menor a 200, utilizaremos la vista hacia el norte
            vista = aula + 'N'
        elif dia >= 200: # Si el d'ia es mayor a 200, utilizaremos la vista hacia el sur
            vista = aula + 'S'
    os.system('evalglare -c temp.hdr ../resultados/revision_Ib/foto/{}_{}-{}-ab{}.hdr >> ../resultados/revision_Ib/glare.txt'.format(vista,dia,hora,ab))
    os.system('pfilt -e -0.5 temp.hdr > ../resultados/revision_Ib/glare/{}_{}-{}.hdr'.format(vista,dia,hora))
    os.system('rm temp.hdr')

for aula in ['A10-1','A10-2','A20-1','A20-2','A40-1','A40-2']: # En las siguientes líneas determinamos los dias y horas de evaluacion de acuerdo al aula
    if 'A10' in aula:
        dias = [356,346,326,316]
    elif 'A20' in aula:
        dias = [171,156,149]
    elif 'A40' in aula:
        dias = [171,156,149,356,346,326,316]

    for dia in dias:
        if dia in [171,156,149]:
            hora = 18
        elif dia in [356,346,326,316]:
            hora = 9
        revision_Ib(aula, dia, hora) # imagenes con ab = 0
        revision_Ib(aula, dia, hora, 10) # imagenes con ab = 10, para usar con evalglare
        revision_glare(aula, dia, hora) # analisis con evalglare, ab = 10 default
        print('Aula {} lista'.format(aula))
