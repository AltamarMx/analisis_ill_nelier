# Programa para convertir de hdr a jpeg todos los archivos .hdr contenidos en ruta. Si se desea conservar los archivos .tiff, comentar ultima linea.
import os
ruta = '../resultados/revision_Ib/glare/'
archivos = os.listdir(ruta)
for hdr in archivos:
    if '.hdr' in hdr:
        tiff = ruta + hdr.replace('.hdr','.tiff')
        jpg = ruta + hdr.replace('.hdr','.jpg')
        os.system('ra_tiff {} {}'.format(ruta + hdr,tiff))
        os.system('magick {} {}'.format(tiff,jpg))
os.system('rm {}*.tiff'.format(ruta))
