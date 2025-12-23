PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS interaction_rules;
DROP TABLE IF EXISTS prescriptions;
DROP TABLE IF EXISTS inventory;
DROP TABLE IF EXISTS medications;
DROP TABLE IF EXISTS patients;

CREATE TABLE patients (
  patient_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  language_preference TEXT NOT NULL CHECK(language_preference IN ('he','en'))
);

CREATE TABLE medications (
  med_id TEXT PRIMARY KEY,
  brand_name TEXT NOT NULL,
  generic_name TEXT NOT NULL,
  active_ingredients TEXT NOT NULL,
  form TEXT NOT NULL,
  strength TEXT NOT NULL,
  rx_required INTEGER NOT NULL CHECK(rx_required IN (0,1)),
  standard_instructions TEXT NOT NULL,
  common_side_effects TEXT NOT NULL,
  warnings TEXT NOT NULL
);

CREATE TABLE inventory (
  med_id TEXT PRIMARY KEY REFERENCES medications(med_id) ON DELETE CASCADE,
  qty_on_hand INTEGER NOT NULL CHECK(qty_on_hand >= 0),
  reorder_threshold INTEGER NOT NULL DEFAULT 0 CHECK(reorder_threshold >= 0),
  location_bin TEXT
);

CREATE TABLE prescriptions (
  rx_id TEXT PRIMARY KEY,
  patient_id TEXT NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
  med_id TEXT NOT NULL REFERENCES medications(med_id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK(status IN ('active','refill_pending','expired','cancelled')),
  expires_at TEXT NOT NULL, -- YYYY-MM-DD
  refills_remaining INTEGER NOT NULL CHECK(refills_remaining >= 0),
  directions TEXT NOT NULL,
  last_filled_at TEXT
);

CREATE TABLE interaction_rules (
  rule_id TEXT PRIMARY KEY,
  med_id_a TEXT NOT NULL REFERENCES medications(med_id) ON DELETE CASCADE,
  med_id_b TEXT NOT NULL REFERENCES medications(med_id) ON DELETE CASCADE,
  level TEXT NOT NULL CHECK(level IN ('none','caution','avoid')),
  message TEXT NOT NULL,
  source TEXT
);

-- Indexes for speed
CREATE INDEX IF NOT EXISTS idx_meds_brand
ON medications(brand_name);

CREATE INDEX IF NOT EXISTS idx_meds_generic
ON medications(generic_name);

CREATE INDEX IF NOT EXISTS idx_rx_patient_med
ON prescriptions(patient_id, med_id);

-- Prevent duplicate
CREATE UNIQUE INDEX IF NOT EXISTS idx_interaction_pair
ON interaction_rules(med_id_a, med_id_b);

CREATE INDEX IF NOT EXISTS idx_interaction_level
ON interaction_rules(level);