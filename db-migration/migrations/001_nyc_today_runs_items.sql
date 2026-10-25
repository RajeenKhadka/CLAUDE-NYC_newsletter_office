-- NYC Today: one row per agent run, one row per item a researcher found.
-- Item text fields mirror the office's item JSON, renamed to snake_case
-- (confirmedOn -> confirmed_on, sourceDate -> source_date).
-- Absent optional values are NULL, never ''.

create schema if not exists nyc_today;

create table nyc_today.runs (
    run_id       text primary key,                 -- 'run-<ms>', 'chk-<ms>' or 'mgr-<ms>'
    date         date not null,                    -- the New York day the run is about
    agent        text not null
                 check (agent in ('rio', 'fern', 'basil', 'juno', 'vera', 'boss')),
    target       text                              -- the researcher Vera checked
                 check (target in ('rio', 'fern', 'basil', 'juno')),
    model        text not null check (model in ('opus', 'sonnet')),
    items        integer check (items >= 0),
    total_tokens integer check (total_tokens >= 0), -- NULL when usage was not reported
    tool_uses    integer check (tool_uses >= 0),
    duration_ms  integer check (duration_ms >= 0),
    finished_at  timestamptz not null,
    -- only Vera's checks have a target
    check ((agent = 'vera') = (target is not null)),
    -- lets items prove their agent and date match their run
    unique (run_id, agent, date)
);

create table nyc_today.items (
    id           bigint generated always as identity primary key,
    run_id       text not null,
    ref          text not null check (ref ~ '^(rio|fern|basil|juno):[0-9]+$'),
    date         date not null,
    agent        text not null check (agent in ('rio', 'fern', 'basil', 'juno')),
    section      text not null,

    -- required: never NULL, never blank
    name         text not null check (btrim(name) <> ''),
    venue        text not null check (btrim(venue) <> ''),
    url          text not null check (url ~ '^https?://'),
    summary      text not null check (btrim(summary) <> ''
                     and array_length(regexp_split_to_array(btrim(summary), '\s+'), 1) <= 15),
    neighborhood text not null check (btrim(neighborhood) <> ''),
    borough      text not null
                 check (borough in ('Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island')),
    time         text not null check (btrim(time) <> ''),
    price        text not null check (btrim(price) <> ''),
    -- street only: no ', NY' and no trailing ZIP
    address      text not null check (btrim(address) <> ''
                     and address !~* ',\s*NY\M'
                     and address !~ '\m[0-9]{5}(-[0-9]{4})?\s*$'),

    -- optional: NULL when absent, never ''
    condition    text check (btrim(condition) <> ''),
    overview     text check (btrim(overview) <> ''
                     and array_length(regexp_split_to_array(btrim(overview), '\s+'), 1) <= 30),

    -- internal: for Vera and metrics, never shown to readers
    confirmed_on text not null check (btrim(confirmed_on) <> '' and char_length(confirmed_on) <= 80),
    source_date  date,
    verdict      text check (verdict in ('ok', 'fix', 'drop')),  -- NULL until Vera checks it

    created_at   timestamptz not null default now(),

    foreign key (run_id, agent, date) references nyc_today.runs (run_id, agent, date),
    -- each researcher has exactly one section
    check ((agent, section) in (('rio', 'Happy Hours'), ('fern', 'Free Events'),
                                ('basil', 'Food'), ('juno', 'Music'))),
    -- tiers for Happy Hours and Food; Music and Free Events keep exact prices
    check (section not in ('Happy Hours', 'Food') or price in ('$', '$$', '$$$', 'Free')),
    -- a rerun on the same day gets its own run_id, so both runs are kept
    unique (run_id, ref)
);

create index items_date_agent_idx on nyc_today.items (date, agent);
create index runs_date_agent_idx on nyc_today.runs (date, agent);
