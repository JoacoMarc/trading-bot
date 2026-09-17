# ADR-0013 — Papers aislados y Telegram compartido

Aceptado para implementación el 2026-09-17. Cada estrategia paper es un proceso con
DB, saldo, logs y controles propios. Un Compose separado del proyecto operativo
contiene las candidatas; no se escala el servicio actual ni se comparte su DB.

Un solo receptor de comandos Telegram (la referencia). Las candidatas usan el mismo
token/chat exclusivamente para enviar, sin polling ni borrar updates pendientes.
Todos los mensajes llevan identidad y modo. Los comandos afectan solo a la referencia.

Los avisos de operaciones se guardan en una tabla adicional de la misma transacción
SQLite que el fill. Un emisor asíncrono entrega después del commit, reintenta y recupera
pendientes al reiniciar. Identificador único por instancia/operación/categoría.
La tabla es aditiva: lectores/escritores anteriores ignoran la tabla, schema v1 permanece
compatible. No se generan avisos retroactivos a partir de fills anteriores al despliegue.
Entrega al menos una vez: un crash tras aceptación remota y antes del acuse local puede
duplicar un mensaje. Telegram caído no bloquea el trading; fallar al persistir la transacción
local sí impide confirmar un ciclo incompleto. Los demás avisos conservan su cola acotada.

Solo candidatas A aprobadas por Gate 1 pueden desplegarse. B se compara en backtest.
Los capitales independientes no se suman como rendimiento de una cartera compartida.
