import os
from pathlib import Path

# ------------------------------
# Configuración básica de paths
# ------------------------------
BASE   = Path("../modelo")
WEA    = BASE / "Temixco_dias.wea"

SKIES  = BASE / "skies"
MATS   = BASE / "materiales.rad"
MATS_BLACK = BASE / "materiales_black.rad"      # <-- debes crearlo
MATRICES = BASE / "matrices"
OCTREES  = BASE / "octrees"
RESULTS  = BASE / "resultados" / "iluminancia_DDS"

# Archivos de cielo/matrices
SMX_FULL   = MATRICES / "anual_m4.smx"          # cielo completo MF:4
SMX_DIRECT = MATRICES / "anual_m4_direct.smx"   # cielo directo MF:4
SMX_SUN_M6 = MATRICES / "Temixco_sunM6.smx"     # 5165 soles (MF:6)

# Archivos de cielo para rfluxmtx / rcontrib
DC_SKY = SKIES / "dc_sky_noground.rad"          # ya lo tienes
SUNS_RAD = SKIES / "suns.rad"                   # lo creamos abajo

aulas = ["A40-1", "A40-2"]

# Crear directorios si no existen
for d in [SKIES, MATRICES, OCTREES, RESULTS]:
    d.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------
# 0) Sky-matrices: completo, directo, y de soles
# -------------------------------------------------
print(">>> Generando sky-matrix completo MF:4")
os.system(f"gendaymtx -m 4 {WEA} > {SMX_FULL}")

print(">>> Generando sky-matrix DIRECTO MF:4")
os.system(f"gendaymtx -m 4 -d {WEA} > {SMX_DIRECT}")

print(">>> Generando sun-matrix con 5165 soles (MF:6)")
# -5 0.533 = diámetro aparente del sol en grados, consistente con el tutorial DDS
os.system(f"gendaymtx -5 0.533 -d -m 6 {WEA} > {SMX_SUN_M6}")

# -------------------------------------------------
# 1) Crear definición de soles (suns.rad) y octree base para DDS
# -------------------------------------------------
print(">>> Creando definición de fuente 'solar' y discos para 5165 soles (MF:6)")
# Fuente de luz "solar"
os.system(f'echo "void light solar 0 0 3 1e6 1e6 1e6" > {SUNS_RAD}')

# 5165 discos solares usando reinsrc.cal (MF:6)
# Asumimos que reinsrc.cal está en tu RAYPATH
os.system(
    "cnt 5165 | "
    "rcalc -e MF:6 -f /usr/local/radiance/lib/reinsrc.cal "
    "-e Rbin=recno "
    f"-o 'solar source sun 0 0 4 ${{Dx}} ${{Dy}} ${{Dz}} 0.533' >> {SUNS_RAD}"
)

# -------------------------------------------------
# Bucle sobre aulas: DC, DC-directo, sun-coeffs y combinación final
# -------------------------------------------------
for aula in aulas:
    print(f"\n================ AULA {aula} ================\n")

    pts_file = BASE / "objects" / f"{aula}.pts"
    rad_room = BASE / f"{aula}.rad"
    rad_room_black = BASE / f"{aula}_black.rad"   # <-- deberás crearlo
    # (si tienes las ventanas en un archivo aparte, podrías definirlo aquí)
    # glazing_rad = BASE / "ventanas.rad"        # opcional

    # ---------------------------
    # Paso 1: Daylight Coefficients (C_dc)
    # ---------------------------
    dc_mtx = MATRICES / f"{aula}_dc.mtx"
    dc_ill = RESULTS / f"{aula}_dc.ill"

    print(f">>> [Paso 1] DC completo para {aula}")
    os.system(
        "rfluxmtx "
        f"< {pts_file} "
        "-I+ -v "
        "-ab 10 -ad 65536 -dj 1 -dp 1 -dt 0 -dc 1 -as 2048 -lw 1e-6 -n 6 "
        f"- {DC_SKY} {MATS} {rad_room} "
        f"> {dc_mtx}"
    )

    print(f">>> [Paso 1] dctimestep C_dc ⨉ S_full → {dc_ill}")
    os.system(
        f"dctimestep {dc_mtx} {SMX_FULL} | "
        "rmtxop -fa -c 47.7 119.9 11 - "
        f"> {dc_ill}"
    )

    # ---------------------------
    # Paso 2: DC SOLO DIRECTO (C_dcd)
    # ---------------------------
    dcd_mtx = MATRICES / f"{aula}_dcd.mtx"
    dcd_ill = RESULTS / f"{aula}_dcd.ill"

    print(f">>> [Paso 2] DC directo (escena negra) para {aula}")
    # Igual que antes pero:
    #   - escena negra (materiales_black + {aula}_black.rad)
    #   - menor profundidad de rebotes (-ab 1)
    os.system(
        "rfluxmtx "
        f"< {pts_file} "
        "-I+ -v "
        "-ab 1 -ad 65536 -dj 1 -dp 1 -dt 0 -dc 1 -as 2048 -lw 1e-6 -n 6 "
        f"- {DC_SKY} {MATS_BLACK} {rad_room_black} "
        f"> {dcd_mtx}"
    )

    print(f">>> [Paso 2] dctimestep C_dcd ⨉ S_direct → {dcd_ill}")
    os.system(
        f"dctimestep {dcd_mtx} {SMX_DIRECT} | "
        "rmtxop -fa -c 47.7 119.9 11 - "
        f"> {dcd_ill}"
    )

    # ---------------------------
    # Paso 3: Sun coefficients (C_sun) usando rcontrib
    # ---------------------------
    cds_mtx = MATRICES / f"{aula}_cdsDDS.mtx"
    cds_ill = RESULTS / f"{aula}_cds.ill"

    # Octree para sun-coeffs: escena negra + discos solares + (opcional) materiales/ventanas
    sun_oct = OCTREES / f"sunCoefficientsDDS_{aula}.oct"

    print(f">>> [Paso 3] oconv (escena negra + soles) para {aula}")
    # Aquí se sigue muy de cerca el ejemplo del DDS:
    #   materialBlack.rad + roomBlack.rad + suns.rad + materiales/ventanas, etc.
    # Adapta la lista de .rad según tu escena.
    os.system(
        f"oconv -f {MATS_BLACK} {rad_room_black} {SUNS_RAD} {MATS} "
        f"> {sun_oct}"
    )

    # Contar sensores para usar -y en rcontrib (opcional, pero ordena la matriz)
    with open(pts_file, "r") as f:
        n_pts = sum(1 for _ in f if f.readline is not None)

    print(f">>> [Paso 3] rcontrib sun-coeffs (C_sun) para {aula} (Npts={n_pts})")
    # Comando basado en el apéndice B: rcontrib + reinhart.cal + MF:6 + 'solar'
    os.system(
        "rcontrib "
        "-I+ "
        f"-y {n_pts} "
        "-ab 1 -n 6 -ad 256 -lw 1.0e-3 -dc 1 -dt 0 -dj 0 -faf "
        "-e MF:6 -f reinhart.cal -b rbin -bn Nrbins "
        f"-m solar {sun_oct} "
        f"< {pts_file} "
        f"> {cds_mtx}"
    )

    print(f">>> [Paso 3] dctimestep C_sun ⨉ S_sunM6 → {cds_ill}")
    os.system(
        f"dctimestep {cds_mtx} {SMX_SUN_M6} | "
        "rmtxop -fa -c 47.7 119.9 11 - "
        f"> {cds_ill}"
    )

    # ---------------------------
    # Paso 4: Combinar términos DDS
    #         E = C_dc S_full - C_dcd S_direct + C_sun S_sun
    # ---------------------------
    final_ill = RESULTS / f"{aula}_anual_DDS.ill"

    print(f">>> [Paso 4] Combinando términos DDS para {aula} → {final_ill}")
    os.system(
        f"rmtxop {dc_ill} + "
        f"-s -1 {dcd_ill} + "
        f"{cds_ill} "
        f"> {final_ill}"
    )

print("\n>>> Listo. Los resultados DDS están en:", RESULTS)
