#!/usr/bin/env bash
# Script para simular un instante puntual con Radiance para el aula A40-1.
# Ajusta las variables del bloque "Parámetros a editar" con el día/hora deseado,
# y asegúrate de que los valores de irradiancia directa y difusa existan en el WEA.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODEL_DIR="${PROJECT_ROOT}/modelo"
RESULTS_ROOT="${PROJECT_ROOT}/resultados_codex"

# ------------------------------------------------------------
# Parámetros a editar
# ------------------------------------------------------------
SPACE_ID="A40-1"
EPW_FILE="${MODEL_DIR}/nelier_26jun_20novCST.epw"
TARGET_YEAR=2024            # Solo para etiquetar resultados
TARGET_MONTH=6              # Mes (1-12)
TARGET_DAY=26               # Día (1-31)
TARGET_HOUR=10              # Hora local (0-23)
TARGET_MINUTE=0             # Minuto local (0-59)
CENTER_OFFSET=0.5           # 0.5 para datos horarios EPW (centro del intervalo). Ajusta si tu WEA usa otro esquema.

# Opciones Radiance (ajusta según tu criterio de calidad/tiempo)
RT_OPTS="-ab 8 -ad 4096 -as 1024 -aa 0.10 -ar 256 -lw 1e-5 -lr 10 -dj 0.7 -ds 0.15 -dt 0.05 -dc 0.75 -dr 3"

# ------------------------------------------------------------

GEOMETRY_FILE="${MODEL_DIR}/${SPACE_ID}.rad"
POINTS_FILE="${MODEL_DIR}/objects/${SPACE_ID}.pts"
SPACE_RESULTS="${RESULTS_ROOT}/${SPACE_ID}"
mkdir -p "${SPACE_RESULTS}"

for cmd in epw2wea gendaylit oconv rtrace rcalc awk; do
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        echo "Error: no se encontró el comando requerido '${cmd}' en el PATH." >&2
        exit 1
    fi
done

if [ ! -f "${EPW_FILE}" ]; then
    echo "Error: no existe el archivo EPW en ${EPW_FILE}" >&2
    exit 1
fi

if [ ! -f "${GEOMETRY_FILE}" ]; then
    echo "Error: no existe el archivo de geometría ${GEOMETRY_FILE}" >&2
    exit 1
fi

if [ ! -f "${POINTS_FILE}" ]; then
    echo "Error: no existe el archivo de sensores ${POINTS_FILE}" >&2
    exit 1
fi

# Decimal local (hora + minuto) ajustada con el offset del WEA.
LOCAL_DECIMAL=$(awk -v h="${TARGET_HOUR}" -v m="${TARGET_MINUTE}" -v offset="${CENTER_OFFSET}" 'BEGIN { printf("%.3f", h + (m/60.0) + offset); }')
TIMESTAMP=$(printf "%02d%02d_%02d%02d" "${TARGET_MONTH}" "${TARGET_DAY}" "${TARGET_HOUR}" "${TARGET_MINUTE}")

# Convertimos EPW a WEA específico para esta corrida y obtenemos los datos solares del encabezado del EPW.
WEA_FILE="${SPACE_RESULTS}/${SPACE_ID}_${TARGET_YEAR}_codex.wea"
echo "• Generando WEA temporal en ${WEA_FILE}"
epw2wea "${EPW_FILE}" "${WEA_FILE}"

IFS=',' read -r _ _ _ _ _ _ EPW_LAT EPW_LON EPW_TZ _ < "${EPW_FILE}"
if [ -z "${EPW_LAT}" ] || [ -z "${EPW_LON}" ] || [ -z "${EPW_TZ}" ]; then
    echo "Error: no se pudieron leer latitud/longitud/huso del EPW." >&2
    exit 1
fi

LATITUDE=$(awk -v v="${EPW_LAT}" 'BEGIN { printf("%.6f", v); }')    # N positivo (igual que EPW)
LONGITUDE=$(awk -v v="${EPW_LON}" 'BEGIN { printf("%.6f", -v); }')  # Radiance: Oeste positivo
MERIDIAN=$(awk -v tz="${EPW_TZ}" 'BEGIN { printf("%.6f", -tz * 15.0); }') # Radiance: Oeste positivo


# Recuperamos irradiancia directa normal y difusa horizontal para el instante deseado.
read -r DIR_NORM DIFF_HORIZ <<< "$(awk -v m="${TARGET_MONTH}" -v d="${TARGET_DAY}" -v target="${LOCAL_DECIMAL}" '
    NR > 6 && $1 == m && $2 == d {
        if (sprintf("%.3f", $3) == sprintf("%.3f", target)) {
            print $4, $5;
            exit;
        }
    }
' "${WEA_FILE}")"

if [ -z "${DIR_NORM}" ] || [ -z "${DIFF_HORIZ}" ]; then
    echo "Error: no encontré datos en el WEA para ${TARGET_MONTH}/${TARGET_DAY} a hora decimal ${LOCAL_DECIMAL}." >&2
    echo "       Revisa el archivo ${WEA_FILE} y ajusta TARGET_HOUR, TARGET_MINUTE o CENTER_OFFSET." >&2
    exit 1
fi

SKY_FILE="${SPACE_RESULTS}/sky_${SPACE_ID}_${TIMESTAMP}_codex.rad"
OCTREE_FILE="${SPACE_RESULTS}/${SPACE_ID}_${TIMESTAMP}_codex.oct"
ILL_FILE="${SPACE_RESULTS}/${SPACE_ID}_${TIMESTAMP}_codex.ill"

echo "• Generando cielo con gendaylit (Dir=${DIR_NORM} W/m², Dif=${DIFF_HORIZ} W/m²)"
{
    echo "# Sky generado por run_radiance_A40-1_codex.sh"
    echo "# Fecha: ${TARGET_YEAR}-${TARGET_MONTH}-${TARGET_DAY} ${TARGET_HOUR}:${TARGET_MINUTE} (decimal ${LOCAL_DECIMAL})"
    gendaylit "${TARGET_MONTH}" "${TARGET_DAY}" "${LOCAL_DECIMAL}" -W "${DIR_NORM}" "${DIFF_HORIZ}" -a "${LATITUDE}" -o "${LONGITUDE}" -m "${MERIDIAN}"
} > "${SKY_FILE}"

echo "• Construyendo octree en ${OCTREE_FILE}"
(
    cd "${SCRIPT_DIR}"
    oconv "${SKY_FILE}" "${GEOMETRY_FILE}" > "${OCTREE_FILE}"
)

if command -v nproc >/dev/null 2>&1; then
    NPROC=$(nproc)
elif command -v sysctl >/dev/null 2>&1; then
    NPROC=$(sysctl -n hw.ncpu 2>/dev/null || echo 1)
else
    NPROC=1
fi
[ -z "${NPROC}" ] && NPROC=1

TMP_ILL=""
cleanup() {
    if [ -n "${TMP_ILL}" ] && [ -f "${TMP_ILL}" ]; then
        rm -f "${TMP_ILL}"
    fi
}
trap cleanup EXIT
TMP_ILL=$(mktemp "${SPACE_RESULTS}/.${SPACE_ID}_${TIMESTAMP}_codex_XXXXXX")

echo "• Ejecutando rtrace con ${NPROC} hilos"
rtrace -n "${NPROC}" -I+ -h -w ${RT_OPTS} "${OCTREE_FILE}" < "${POINTS_FILE}" \
    | rcalc -e '$1=47.4*$1+119.9*$2+11.6*$3' > "${TMP_ILL}"

{
    echo "# x y z Nx Ny Nz Illuminancia_lux"
    paste "${POINTS_FILE}" "${TMP_ILL}"
} > "${ILL_FILE}"

echo "• Resultado de sensores guardado en ${ILL_FILE}"
echo "• Archivos auxiliares:"
echo "    ├─ Cielo : ${SKY_FILE}"
echo "    └─ Octree: ${OCTREE_FILE}"
*** End Patch
