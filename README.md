# Sheet-Manager

App Streamlit per gestire le schede dei personaggi del sistema **STATISFY / Aethermoor**.
Multi-utente (master + giocatori), schema stat flessibile per personaggio,
HP/Mana/Ki dinamici, formule derivate scriptabili dal master, importer Excel.

## Setup locale

```bash
pip install -r requirements.txt

# 1. Avvia Postgres (qualunque modo va bene)
docker run --name pg-sheet -e POSTGRES_PASSWORD=test -p 5432:5432 -d postgres:16

# 2. Variabili d'ambiente
export DATABASE_URL="postgresql://postgres:test@localhost:5432/postgres"
export BOOTSTRAP_MASTER_USERNAME="master"
export BOOTSTRAP_MASTER_PASSWORD="test1234"

# 3. Crea schema + master + ruleset di default
python -m scripts.init_db

# 4. (Opzionale) Importa la scheda di Kelvin assegnandola al master
python -m scripts.import_kelvin master

# 5. Avvia
streamlit run app.py
```

Apri http://localhost:8501 e accedi con `master / test1234`.

## Deploy su Streamlit Community Cloud

1. **Push** del repo su GitHub.
2. **Supabase** (o altro Postgres free): crea un progetto, copia la connection string.
3. **Streamlit Cloud** → New app → seleziona il repo, file principale `app.py`.
4. **App settings → Secrets**:
   ```toml
   DATABASE_URL = "postgresql://postgres:...@.../postgres?sslmode=require"
   BOOTSTRAP_MASTER_USERNAME = "master"
   BOOTSTRAP_MASTER_PASSWORD = "una-password-forte"
   BOOTSTRAP_MASTER_DISPLAY_NAME = "Game Master"
   DEFAULT_CAMPAIGN_NAME = "Aethermoor"
   ```
5. Al primo avvio l'app crea schema, master e ruleset di default. Login → tab **Admin** → **Import / Export** per caricare la scheda Excel di un personaggio.

## Architettura

```
app.py                     login + landing
pages/
  1_Scheda.py              stat, HP/MP, level-up, derivate
  2_Skills.py              albero skill, add/edit, skill correlate
  3_Talenti.py             talenti & titoli (con bonus stat in JSON)
  4_Pets.py                pet e loro skill
  5_Inventario.py          editor tabellare con peso totale
  6_Quest.py
  7_Maledizioni.py
  8_Admin.py               (master) CRUD utenti / personaggi / ruleset / import
src/
  db.py, models.py         SQLAlchemy 2.x
  auth.py                  bcrypt + role guards
  formulas.py              simpleeval (no eval), funzioni whitelist
  calc.py                  compute_character_state()
  actions.py               level_up, add_skill/stat/resource/derived
  ui_components.py         barre risorse, badge rarita
  page_utils.py            sidebar, character selector
  importer.py              parse del template Excel STATISFY
scripts/
  init_db.py               schema + bootstrap idempotente
  import_kelvin.py         seed: importa Kelvin dal file in data/seed/
data/seed/
  Scheda_Personaggio_STATISFY_Kelvin.xlsx
```

## Modello dati e logica

- Ogni personaggio ha **stat / risorse / derivate** propri (snapshot mutabile dal ruleset).
  Il master puo aggiungere a ognuno qualcosa di unico (es. risorsa `KI`).
- Le **stat** sono la somma di sei contributi:
  `iniziale + creazione + investiti + level-up + altro + bonus titoli`.
  Solo "investiti" e "altro" sono modificabili dal giocatore.
- Le **formule** (max HP, derivate) sono testo libero valutato da `simpleeval`
  con whitelist: `+ - * / ** %`, `min`, `max`, `abs`, `round`, `floor`, `ceil`, `sqrt`.
  I nomi sono le `key` delle stat del personaggio (case-sensitive) e `LEVEL`.
- **Level-up**: `level += 1`, ogni stat non-custom riceve `+1` in `value_levelup`,
  il pool di punti liberi cresce di `levelup_pool_per_level` (default 10),
  le risorse (HP/MP/...) tornano al massimo se il toggle e attivo.
- **Permessi**: matrice in `src/auth.py` e `src/page_utils.can_edit`.
  Master = tutto; giocatore = CRUD sui suoi, lettura sugli altri.

## Interrogare il DB

### Dall'app (raccomandato)
Login come master → pagina **Database** (icona chiave inglese in sidebar). Tre tab:
- **Personaggi**: scollega proprietario, trasferisci PG, elimina con cascata.
- **Tabelle**: browser/editor di qualsiasi tabella. Le password sono mascherate.
- **SQL Console**: query libere. Read-only di default; per `INSERT/UPDATE/DELETE/DDL` attiva il toggle "Modalità scrittura" (si resetta al reload).

### Locale (SQLite)
```bash
sqlite3 local.db
.tables
.schema characters
SELECT id, name, level, owner_id FROM characters;
```
GUI consigliate: **DB Browser for SQLite**, **DBeaver**, **TablePlus**.

### Produzione (Supabase Postgres)
- **SQL Editor di Supabase**: pannello web → "SQL Editor" → query libere.
- **psql da terminale**:
  ```bash
  psql "$DATABASE_URL"
  \dt                       # lista tabelle
  \d characters             # schema tabella
  SELECT * FROM users;
  ```
- **DBeaver / TablePlus**: nuova connessione Postgres con la connection string Supabase (host, port, database, user, password, sslmode=require).

### Esempi utili
```sql
-- Tutti i PG con owner
SELECT c.id, c.name, c.level, u.username
FROM characters c LEFT JOIN users u ON u.id = c.owner_id
ORDER BY c.name;

-- Stat di Kelvin con totale calcolato
SELECT key, label, value_initial + value_creation + value_invested
       + value_levelup + value_other AS total
FROM character_stats
WHERE character_id = (SELECT id FROM characters WHERE name='Kelvin');

-- Scollegare manualmente un proprietario
UPDATE characters SET owner_id = NULL WHERE id = 1;
```

## Note operative

- `init_db.py` e idempotente: si puo rilanciare in sicurezza dopo modifiche schema.
  Per migrazioni complesse usare Alembic (non incluso in questa versione).
- Le password sono hashate con bcrypt; il bootstrap genera l'hash al primo avvio.
- Il file `.streamlit/secrets.toml` non va mai committato (vedi `.gitignore`).
