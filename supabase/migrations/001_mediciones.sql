create table public.mediciones (
  orden bigint generated always as identity primary key,
  id uuid not null unique,
  departamento text not null check (departamento in (
    '01', '02', '03', '04', '05', '06', '07', '08',
    '09', '10', '11', '12', '13', '14', '15'
  )),
  partida integer not null check (partida between 1 and 27),
  fecha date not null check (fecha between date '0001-01-01' and date '9999-12-31'),
  avance numeric not null check (avance between 0 and 100),
  observaciones text not null default '' check (char_length(observaciones) <= 500)
);

alter table public.mediciones enable row level security;

-- El tablero compartido es de acceso abierto. La API solo admite añadir mediciones.
revoke all on public.mediciones from public, anon, authenticated;
grant select on public.mediciones to anon, authenticated;
grant insert (id, departamento, partida, fecha, avance, observaciones)
  on public.mediciones to anon, authenticated;
grant usage on sequence public.mediciones_orden_seq to anon, authenticated;

create policy "Consultar mediciones" on public.mediciones
  for select to anon, authenticated using (true);
create policy "Añadir mediciones" on public.mediciones
  for insert to anon, authenticated with check (true);
