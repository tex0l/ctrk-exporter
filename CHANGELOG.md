# Changelog

## v0.3.1 — 5 février 2026 (état actuel)

Parser v7 — 1031 lignes | Spec v2.1 | 94.9% match rate (47 fichiers, 22 canaux validés vs natif)

### Parser

- **Lean signé** (`lean_signed_deg`) : nouveau canal préservant la direction de l'inclinaison (négatif/positif) au lieu de la valeur absolue produite par le natif. Même formule de calibration, même deadband et arrondi, mais le signe de `sum_val - 9000` est conservé. Le canal `lean_deg` (absolu, compatible natif) est inchangé.

---

## v0.3.0 — 5 février 2026

Parser v7 — 1021 lignes | Spec v2.1 | 94.9% match rate (47 fichiers, 22 canaux)

### Parser

- **Mode natif per-lap** (`--native`) : nouveau chemin de parsing qui réinitialise l'état à chaque tour, répliquant l'architecture per-lap de `libSensorsRecordIF.so`. Atteint 95.6% de match global et 98.7% sur `fuel_cc` (vs 86.5% en mode continu).
- **Décodage structuré du header** (`_find_data_start`) : remplace le pattern-matching naïf par une lecture correcte des entrées header (RECORDLINE, CCU_VERSION, etc.) à partir de l'offset 0x34.
- **Conversion timestamp native** (`_get_time_data`) : implémente l'algorithme exact du natif (`GetTimeData` @ 0xdf40) avec gestion du millis wrapping (retour en arrière du compteur millisecondes).
- **État initial à zéro** : les valeurs par défaut de lean, pitch, acc_x, acc_y passent de leur offset neutre (9000, 30000, 7000, 7000) à 0, en accord avec le `memset(0)` du natif.
- **Reset de l'horloge d'émission** aux marqueurs type-5 (Lap), améliorant le match RPM de ~77% à ~83%.
- **Suppression du code mort** : import `re` inutilisé, dict `CAN_DLC` jamais référencé, compteurs (`gps_count`, `can_count`, `checksum_failures`) incrémentés mais jamais lus dans `_parse_lap_range`, fonction `ensure_output_dir()` orpheline, variables inutilisées.
- **Docstring** : v6 → v7.

### CLI

- **Flag `--native`** sur la commande `parse` pour activer le mode per-lap.
- Import `re` déplacé au top-level, `import os` inutilisé supprimé.
- Variables inutilisées `setup_parser` / `clean_parser` nettoyées.

### Spécification format (v2.0 → v2.1)

- **v2.0** : réécriture complète. Header structuré 14 octets au lieu de pattern-matching. Documentation de : coordonnées GPS void (9999, 9999), accumulateur fuel avec reset par tour, exemples hex complets à partir de fichiers réels.
- **v2.1** : comportements natifs uniquement — vérification delta temporelle à 3 bandes (seuil secondaire 10ms @ 0xaf1b), limite compteur lignes (72000 @ 0xaece), rejet gear=7 (0xe163), handler CAN 0x051b (0xe102).

### Documentation

- **Nouveau** : `docs/REVIEW_REPORT.md` — rapport de validation avec matrice de conformité spec.
- **Nouveau** : `docs/product/BACKLOG.md` — backlog produit priorisé (7 epics, decision log).
- **Nouveau** : 3 epics détaillés (EPIC-001 Session Summary, EPIC-002 Export Formats, EPIC-003 Python Package).
- **Nouveau** : `src/test_parser_comparison.py` — suite de comparaison Python vs Natif (361 lignes), alignement GPS, tolerances par canal.
- **Supprimé** : `docs/TODO.md` (remplacé par le backlog).
- **Harmonisation** : nombres canoniques (47 fichiers, 22 canaux, 420K+ records, 94.9%) unifiés dans tous les documents. Correction de l'inversion acc_x (Longitudinal) / acc_y (Latéral) dans le README.
- **NATIVE_LIBRARY.md** : sections dupliquées (timestamp CAN, formule LEAN) remplacées par des renvois à la spec. Match rate corrigé de 95.37% à 94.9%.
- **EPIC-001** : références mortes nettoyées (TASK-H3, Rec #5, EPIC-004/005).
- **Agents** (`.claude/agents/`) : CLI correctement décrite comme Python (pas Bash), compteurs de lignes mis à jour, fichiers référencés corrigés.

---

## v0.2.0 — 27 janvier 2026

Parser v6 — 836 lignes | Spec v1.3 | Validation sur 42 fichiers

### Parser

- **Découverte de la structure timestamp CAN** : les octets `E9 07` n'étaient pas un magic number mais l'année 2025 en little-endian (`uint16`, 0x07E9). Le parser lit maintenant le year comme un vrai champ, supportant **tous les fichiers quel que soit la date d'enregistrement** (pas seulement 2025).
- **Correction de l'ordre des bits ABS** : `R_ABS = bit0`, `F_ABS = bit1` (inversés auparavant), conformément au désassemblage natif @ 0xe2b7.
- **Support multi-fichiers** : `./ctrk-exporter parse *.CTRK` traite tous les fichiers d'un coup avec sortie dans un répertoire.
- **Alignement des noms** entre parser et spécification.

### Documentation

- **Spec v1.3** : structure complète des timestamps CAN documentée (8 octets : sec, min, hour, weekday, day, month, year LE).
- **NATIVE_LIBRARY.md** : validation étendue à 42 fichiers sur 4 mois (juillet-octobre 2025), 21 canaux, interface JNI documentée (`GetTotalLap`, `GetLapTimeRecordData`, `GetSensorsRecordData`), architectures supportées.
- **Nouveau** : `docs/TODO.md` — suivi des tâches.

---

## v0.1.0 — 26 janvier 2026

Parser v6 — 836 lignes | Spec v1.2 | Validation sur 1 fichier

### Parser

- **8 CAN IDs décodés** : 0x0209 (RPM/Gear), 0x0215 (Throttle/TCS/SCS/LIF/Launch), 0x023E (Temp/Fuel), 0x0250 (Accel X/Y), 0x0258 (Lean/Pitch), 0x0260 (Brakes), 0x0264 (Wheel Speed), 0x0268 (ABS). Tous vérifiés par désassemblage de `libSensorsRecordIF.so`.
- **21 canaux télémétrie** : 15 analogiques + 6 booléens, avec formules de calibration complètes.
- **Détection de tours** par croisement de la ligne d'arrivée GPS (coordonnées extraites du header).
- **Accumulateur fuel** avec reset par tour.
- **Algorithme LEAN natif** : deadband ±5°, arrondi à la centaine, nibble interleaving.
- **Export CSV** calibré (26 colonnes) + export brut optionnel (`--raw`).

### CLI

- 5 commandes : `parse`, `graph`, `android setup`, `android convert`, `android clean`.
- `parse` : fichier unique avec flag `--raw` et option `-o`.
- `graph` : génération de graphiques par tour (matplotlib/pandas, nécessite venv).
- `android` : pont vers la librairie native via émulateur Android (macOS ARM uniquement).

### Android Bridge

- App Kotlin complète (`android_app/`) avec `NativeBridge.kt`, `SessionContainer.kt`, `TelemetryPoint.kt`.
- Script `build_and_run.sh` pour compilation et exécution.
- Extraction du `.so` depuis l'APK Y-Trac v1.3.8.

### Documentation

- **Spec v1.2** : format binaire documenté (partiellement en français), vérification sur 1 fichier (16 462 points natifs vs 16 475 parser, +0.08%).
- **NATIVE_LIBRARY.md** : notes de reverse engineering initiales.
- **3 docs supplémentaires** : `REVERSE_ENGINEERING_SUMMARY.md`, `libSensorsRecordIF_howitworks.md`, `libSensorsRecordIF_usage.md`.
- **Scripts d'analyse** : `analyze_lean_formula.py`, `compare_raw_values.py`, `compare_values.py`, `extract_ytrac_values.py`, `test_can_parsing.py`, `visualize_comparison.py`, `visualize_ride.py`.
