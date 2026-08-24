// Mongo guarda start_at en UTC pero SIN sufijo "Z" (naive) — si se parsea
// con `new Date(str)` tal cual, JS lo toma como hora local del dispositivo
// y el día/hora calculado queda corrido (ej. un partido a las 21:00 hora
// México se guarda como "03:00" del día siguiente en UTC, y sin forzar el
// parseo como UTC aparece fechado un día después). Forzamos "Z" solo si el
// string no trae ya info de timezone.
export function parseUtc(dateStr: string): Date {
  return new Date(/[Z+-]\d{2}:?\d{2}$|Z$/.test(dateStr) ? dateStr : `${dateStr}Z`);
}
