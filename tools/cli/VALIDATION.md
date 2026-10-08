# Validación del laboratorio y la CLI

Las pruebas públicas usan fixtures de ejemplo, respuestas de IA controladas y
servicios simulados. No incluyen nombres, rutas, código ni reportes de proyectos
privados.

## Resultados

- CLI: 76 pruebas aprobadas, incluida integración real MiniStack/Docker.
- Agent: 345 pruebas aprobadas en Docker con Python 3.13 y uv.lock.
- BFF: 314 pruebas aprobadas y build correcto.
- Frontend: 220 pruebas aprobadas y build correcto.
- Ruff, OpenSpec strict y git diff --check aprobados.
- El lint global frontend/BFF mantiene infracciones anteriores al cambio;
  no se modifican dependencias ni submódulos para corregirlas en esta entrega.

## Cobertura de pruebas

Selección del working tree, ignores, submódulos, snapshot con hashes, paquetes
corruptos, múltiples lotes, validación y recuperación de respuestas de expertos.
Navegación real con flechas/Vim, cancelación, salida, restauración de terminal,
persistencia sin secretos, animación desactivable y presentación de resultados.

Los contratos AWS se prueban con respuestas HTTP controladas: URLs prefirmadas
en mapa/lista, PUT sin clave Titvo, inicio source=cli/full, consulta, errores,
espera acotada y confirmación cancelada. No hay fallback entre destinos.
Los resultados sin hallazgos inline usan la cantidad registrada y el reporte
externo; no se inventan cero hallazgos, duración ni consumo históricos.

## Límites de la validación

MiniStack prueba S3/DynamoDB con un worker Docker real y modelo simulado.
El modo simulado comprueba integración, no detección de vulnerabilidades.
Las pruebas no ejecutan solicitudes a proveedores de IA ni despliegues AWS.
Una verificación contra AWS real requiere una instancia con las ramas del
Agent/API desplegadas, su endpoint y una clave Titvo autorizada.

Las instrucciones reproducibles están en [README.md](README.md).
