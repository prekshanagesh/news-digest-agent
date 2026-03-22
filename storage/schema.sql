create table if not exists feeds(
    id integer primary key autoincrement,
    name text not null,
    url text not null unique,
    category text,
    is_active integer default 1
);

create table if not exists topics(
    id integer primary key autoincrement,
    topic_name text not null,
    keyword text not null,
    is_active integer default 1
);

create table if not exists source_weights(
    id integer primary key autoincrement,
    source_name text not null unique,
    weight real not null default 1.0
);

create table if not exists recipients(
    id integer primary key autoincrement,
    email text not null,
    is_active integer default 1
);

create table if not exists articles(
    id integer primary key autoincrement,
    article_hash text not null unique,
    title text,
    url text,
    source text,
    published_at text,
    topic text,
    topic_score integer,
    summary text,
    score real,
    fetched_at text
);

create table if not exists sent_digest_items(
    id integer primary key autoincrement,
    article_hash text not null,
    sent_date text not null
);

create table if not exists pipeline_runs(
    id integer primary key autoincrement,
    run_started_at TEXT,
    run_finished_at TEXT,
    articles_ingested integer,
    articles_sent integer,
    status text,
    error_message TEXT
);

-- NEW: tracks every link click from the digest email
create table if not exists clicks(
    id integer primary key autoincrement,
    article_hash text not null,
    source text,
    topic text,
    clicked_at text not null,
    sent_date text
);
