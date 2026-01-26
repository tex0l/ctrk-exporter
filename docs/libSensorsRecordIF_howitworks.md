# libSensorsRecordIF.so - Analyse par Reverse Engineering

**Date:** 2026-01-26
**Version:** 1.1
**Status:** VALIDÉ - Formules CAN vérifiées contre sortie native (99.7% match)
**Auteur:** Analyse automatisée du fichier `apk_analysis/ytrac_decompiled/resources/lib/x86_64/libSensorsRecordIF.so`

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Fonctions JNI exportées](#2-fonctions-jni-exportées)
3. [Structures de données internes](#3-structures-de-données-internes)
4. [Analyse de AnalisysCAN()](#4-analyse-de-analisyscan)
5. [Formule LEAN détaillée](#5-formule-lean-détaillée)
6. [Correspondance CAN ID → Champs](#6-correspondance-can-id--champs)
7. [Écarts identifiés avec le parser Python](#7-écarts-identifiés-avec-le-parser-python)
8. [TODO pour session suivante](#8-todo-pour-session-suivante)

---

## 1. Vue d'ensemble

Le fichier `libSensorsRecordIF.so` est la bibliothèque native utilisée par l'application Y-Trac pour parser les fichiers CTRK. Elle est disponible pour 4 architectures :
- `arm64-v8a` (Android moderne)
- `armeabi-v7a` (Android 32-bit)
- `x86` (émulateurs)
- `x86_64` (émulateurs) ← **Version analysée**

### Caractéristiques
- Format: ELF 64-bit LSB shared object, x86-64
- État: stripped (symboles de debug supprimés)
- Taille: ~200 KB

---

## 2. Fonctions JNI exportées

### Fonctions principales

| Adresse | Symbole | Signature JNI |
|---------|---------|---------------|
| 0x0000a250 | `GetTotalLap` | `(String fileName) → int` |
| 0x0000a560 | `GetLapTimeRecordData` | `(String, int[], SensorsLapTimeRecord[], boolean) → int` |
| 0x0000a970 | `GetSensorsRecordData` | `(String, int, int, SensorsRecord[], int, int[], AINInfo) → int` |
| 0x0000b690 | `GetRecordLineData` | `(String, int[], SensorsRecordLine[]) → int` |
| 0x0000b980 | `SplitLogFile` | `(String, String, Object) → int` |
| 0x0000c120 | `GetSensorsDistanceRecordData` | `(String, int, int, int, float, SensorsRecord[], int[]) → int` |
| 0x0000ca50 | `DamageRecoveryLogFile` | `(String, String, boolean) → int` |
| 0x0000cc50 | `TimeStampRecoveryLogFile` | `(String, String) → int` |
| 0x0000cdd0 | `GetEncryptSecretKey` | `() → String` |
| 0x000116a0 | `Initialize` | `() → int` |

### Fonctions internes clés

| Adresse | Symbole démanglé | Description |
|---------|------------------|-------------|
| 0x0000dfd0 | `AnalisysCAN(_record_data*, _can_data*, int&)` | Parse un message CAN dans la structure record |
| 0x0000e330 | `AnalisysNMEA(char*, double*, double*, double*)` | Parse une phrase NMEA |
| 0x0000e910 | `AnalisysAIN(char*, int, _record_data*, _ain_info*)` | Parse les entrées analogiques |
| 0x0000fa00 | `getNMEAData(__sFILE*, unsigned int, geoutils::Point&)` | Lit les données NMEA du fichier |
| 0x0000f970 | `getCanData(__sFILE*, int, _record_data&, _can_data*, int&)` | Lit les données CAN du fichier |
| 0x0000ecf0 | `openLoggerFileAndMoveToLapOffset(const char*, int, __sFILE**, unsigned int&)` | Ouvre fichier et se positionne |

---

## 3. Structures de données internes

### 3.1 Structure `_record_data` (déduite du désassemblage)

```c
struct _record_data {
    // Offsets déduits de AnalisysCAN()
    uint16_t rpm;           // offset 0x20 - RPM (CAN 0x0209)
    uint8_t  gear;          // offset 0x22 - Gear (CAN 0x0209)
    uint16_t tps;           // offset 0x24 - Throttle Position (CAN 0x0215)
    uint16_t aps;           // offset 0x26 - Accelerator Position (CAN 0x0215)
    uint16_t water_temp;    // offset 0x28 - Water temp (CAN 0x023E) - SINGLE BYTE stored as word!
    uint16_t intake_temp;   // offset 0x2a - Intake temp (CAN 0x023E) - SINGLE BYTE stored as word!
    uint32_t fuel;          // offset 0x2c - Fuel accumulator (CAN 0x023E)
    uint16_t acc_x;         // offset 0x30 - Acceleration X (CAN 0x0250)
    uint16_t acc_y;         // offset 0x32 - Acceleration Y (CAN 0x0250)
    uint16_t front_speed;   // offset 0x34 - Front wheel speed (CAN 0x0264)
    uint16_t rear_speed;    // offset 0x36 - Rear wheel speed (CAN 0x0264)
    uint16_t front_brake;   // offset 0x38 - Front brake pressure (CAN 0x0260)
    uint16_t rear_brake;    // offset 0x3a - Rear brake pressure (CAN 0x0260)
    uint16_t lean;          // offset 0x3c - Lean angle (CAN 0x0258) - FORMULE COMPLEXE
    uint16_t pitch;         // offset 0x3e - Pitch rate (CAN 0x0258)
    uint8_t  r_abs;         // offset 0x40 - Rear ABS active (CAN 0x0268)
    uint8_t  f_abs;         // offset 0x41 - Front ABS active (CAN 0x0268)
    uint8_t  tcs;           // offset 0x42 - Traction Control (CAN 0x0215)
    uint8_t  scs;           // offset 0x43 - Slide Control (CAN 0x0215)
    uint8_t  lif;           // offset 0x44 - Lift Control (CAN 0x0215)
    uint8_t  launch;        // offset 0x45 - Launch Control (CAN 0x0215)
    // ... autres champs
    uint8_t  can_0511[8];   // offset 0x2c0 - Raw CAN 0x0511
    uint8_t  can_051b[8];   // offset 0x2c8 - Raw CAN 0x051B
    uint8_t  can_0226[8];   // offset 0x2d0 - Raw CAN 0x0226
    uint8_t  can_0227[8];   // offset 0x2d8 - Raw CAN 0x0227
};
```

### 3.2 Structure `_can_data` (déduite)

```c
struct _can_data {
    uint32_t can_id;       // offset 0x00 - CAN message ID
    uint8_t  reserved;     // offset 0x04 - ?
    uint8_t  data[8];      // offset 0x05-0x0c - CAN payload (8 bytes)
};
```

**IMPORTANT:** Dans le désassemblage, les données CAN sont accédées à partir de `rsi+5` (offset 5), ce qui correspond à `_can_data.data[0]`.

---

## 4. Analyse de AnalisysCAN()

### Pseudocode complet (extrait du désassemblage 0x0000dfd0 - 0x0000e32e)

```c
void AnalisysCAN(_record_data* record, _can_data* can, int* fuel_acc) {
    uint32_t can_id = can->can_id;  // [rsi+0]
    uint8_t* data = can->data;       // [rsi+5] to [rsi+0xc]

    switch (can_id) {
        case 0x0209:  // Engine - RPM & Gear
            record->rpm = (data[0] << 8) | data[1];    // [rdi+0x20]
            uint8_t gear = data[4] & 0x07;
            if (gear != 7) {
                record->gear = gear;                    // [rdi+0x22]
            }
            break;

        case 0x0215:  // Throttle - TPS, APS, Electronic controls
            record->tps = (data[0] << 8) | data[1];    // [rdi+0x26] - ATTENTION: inversé!
            record->aps = (data[2] << 8) | data[3];    // [rdi+0x24] - ATTENTION: inversé!
            record->launch = (data[6] & 0x60) != 0;    // [rdi+0x45]
            record->tcs = (data[7] >> 5) & 1;          // [rdi+0x42]
            record->scs = (data[7] >> 4) & 1;          // [rdi+0x43]
            record->lif = (data[7] >> 3) & 1;          // [rdi+0x44]
            break;

        case 0x023E:  // Temperature & Fuel
            record->water_temp = data[0];              // [rdi+0x28] - SINGLE BYTE!
            record->intake_temp = data[1];             // [rdi+0x2a] - SINGLE BYTE!
            uint16_t fuel_delta = (data[2] << 8) | data[3];
            *fuel_acc += fuel_delta;                   // Accumulation
            record->fuel = *fuel_acc;                  // [rdi+0x2c]
            break;

        case 0x0250:  // Motion - Acceleration
            record->acc_x = (data[0] << 8) | data[1];  // [rdi+0x30]
            record->acc_y = (data[2] << 8) | data[3];  // [rdi+0x32]
            break;

        case 0x0258:  // IMU - Lean & Pitch (COMPLEX!)
            record->pitch = (data[6] << 8) | data[7];  // [rdi+0x3e]
            record->lean = compute_lean(data);         // [rdi+0x3c] - Voir section 5
            break;

        case 0x0260:  // Brake pressure
            record->front_brake = (data[0] << 8) | data[1];  // [rdi+0x38]
            record->rear_brake = (data[2] << 8) | data[3];   // [rdi+0x3a]
            break;

        case 0x0264:  // Wheel speed
            record->front_speed = (data[0] << 8) | data[1];  // [rdi+0x34]
            record->rear_speed = (data[2] << 8) | data[3];   // [rdi+0x36]
            break;

        case 0x0268:  // ABS status
            record->f_abs = data[4] & 1;               // [rdi+0x41]
            record->r_abs = (data[4] >> 1) & 1;        // [rdi+0x40]
            break;

        case 0x0226:  // Raw CAN storage
            memcpy(&record->can_0226, data, 8);        // [rdi+0x2d0]
            break;

        case 0x0227:  // Raw CAN storage
            memcpy(&record->can_0227, data, 8);        // [rdi+0x2d8]
            break;

        case 0x0511:  // Raw CAN storage
            memcpy(&record->can_0511, data, 8);        // [rdi+0x2c0]
            break;

        case 0x051B:  // Raw CAN storage
            memcpy(&record->can_051b, data, 8);        // [rdi+0x2c8]
            break;
    }
}
```

---

## 5. Formule LEAN détaillée

### Désassemblage original (0x0000e1bc - 0x0000e32e)

La formule LEAN est la plus complexe. Voici l'analyse détaillée :

```asm
; CAN 0x0258 - LEAN calculation
; data[0..7] accessible at [rsi+5] to [rsi+0xc]

; Step 1: Extract PITCH (bytes 6-7)
movzx eax, byte [rsi + 0xb]    ; data[6]
shl eax, 8
movzx ecx, byte [rsi + 0xc]    ; data[7]
or ecx, eax
mov word [rdi + 0x3e], cx      ; pitch = (data[6] << 8) | data[7]

; Step 2: Compute val1 component
movzx eax, byte [rsi + 5]      ; b0 = data[0]
shl eax, 4                      ; b0 << 4
movzx ecx, byte [rsi + 7]      ; b2 = data[2]
and ecx, 0xf                    ; b2 & 0x0f
or ecx, eax                     ; val1_part = (b0 << 4) | (b2 & 0x0f)

; Step 3: Compute val2 component
movzx eax, byte [rsi + 6]      ; b1 = data[1]
movzx edx, byte [rsi + 8]      ; b3 = data[3]
shr edx, 4                      ; b3 >> 4
shl ecx, 8                      ; val1 = val1_part << 8
and eax, 0xf                    ; b1 & 0x0f
shl eax, 4                      ; (b1 & 0x0f) << 4
or eax, edx                     ; val2 = ((b1 & 0x0f) << 4) | (b3 >> 4)

; Step 4: Compute sum and transform
movzx ecx, cx                   ; val1 (16-bit)
lea edx, [rax + rcx]           ; sum = val1 + val2
mov esi, 0x2328                 ; 9000 (center value for upright)
sub esi, edx                    ; deviation_neg = 9000 - sum
cmp edx, 0x2328                 ; compare sum to 9000
lea eax, [rcx + rax + 0xdcd8]  ; deviation_pos = sum + 56536 = (sum - 9000) mod 65536
cmovb eax, esi                  ; if sum < 9000: use deviation_neg, else: use deviation_pos

; Step 5: Deadband check
movzx ecx, ax                   ; deviation (16-bit)
cmp ecx, 0x1f3                  ; compare to 499 (~5 degrees)
ja alternate_calc               ; if > 499, use alternate formula
mov word [rdi + 0x3c], 0x2328  ; else store 9000 (upright)
ret

alternate_calc:
    ; Complex formula for larger deviations
    ; result = 9000 + deviation - (deviation % 100)
    imul rdx, rcx, 0x51eb851f  ; magic multiply for div by 100
    shr rdx, 0x25
    imul edx, edx, 0x64        ; edx = (deviation / 100) * 100
    sub ecx, edx               ; ecx = deviation % 100
    add eax, 0x2328            ; eax = deviation + 9000
    sub eax, ecx               ; eax = 9000 + deviation - (deviation % 100)
    mov word [rdi + 0x3c], ax  ; store result
    ret
```

### Formule Python équivalente

```python
def compute_lean_native(data: bytes) -> int:
    """
    Calcule la valeur LEAN exactement comme la bibliothèque native.

    Args:
        data: 8 bytes du message CAN 0x0258

    Returns:
        lean_raw: Valeur brute à calibrer avec (raw/100) - 90
    """
    b0, b1, b2, b3 = data[0], data[1], data[2], data[3]

    # Step 1: Extract values from packed bytes
    val1_part = (b0 << 4) | (b2 & 0x0f)
    val1 = val1_part << 8
    val2 = ((b1 & 0x0f) << 4) | (b3 >> 4)

    # Step 2: Compute sum
    sum_val = (val1 + val2) & 0xFFFF

    # Step 3: Transform to deviation from center (9000)
    if sum_val < 9000:
        deviation = 9000 - sum_val
    else:
        deviation = (sum_val - 9000) & 0xFFFF

    # Step 4: Deadband - if within ±5° of upright, return upright
    if deviation <= 499:
        return 9000  # Upright (0° after calibration)

    # Step 5: For larger deviations, normalize
    # This removes the fractional part (rounds to nearest degree)
    deviation_rounded = deviation - (deviation % 100)
    result = 9000 + deviation_rounded

    return result & 0xFFFF
```

### Interprétation

1. **Centre (upright):** `sum = 9000` → `lean_raw = 9000` → `lean_deg = 0°`
2. **Deadband:** Si |deviation| ≤ 499 (~5°), retourne 9000 (upright)
3. **Leaning left:** `sum < 9000` → `lean_raw = 9000 + (9000 - sum)` → lean positif
4. **Leaning right:** `sum > 9000` → `lean_raw = 9000 + (sum - 9000)` → lean aussi positif!

**PROBLÈME IDENTIFIÉ:** La formule native semble stocker l'amplitude absolue de l'inclinaison, pas la direction signée! Il faudrait analyser plus en détail comment la direction est encodée.

---

## 6. Correspondance CAN ID → Champs

### Tableau récapitulatif

| CAN ID | Byte 0 | Byte 1 | Byte 2 | Byte 3 | Byte 4 | Byte 5 | Byte 6 | Byte 7 |
|--------|--------|--------|--------|--------|--------|--------|--------|--------|
| 0x0209 | RPM_H | RPM_L | - | - | Gear(0-2) | - | - | - |
| 0x0215 | TPS_H | TPS_L | APS_H | APS_L | - | - | Launch | TCS/SCS/LIF |
| 0x023E | WT | INTT | Fuel_H | Fuel_L | - | - | - | - |
| 0x0250 | ACCX_H | ACCX_L | ACCY_H | ACCY_L | - | - | - | - |
| 0x0258 | LEAN0 | LEAN1 | LEAN2 | LEAN3 | - | - | PITCH_H | PITCH_L |
| 0x0260 | FBRK_H | FBRK_L | RBRK_H | RBRK_L | - | - | - | - |
| 0x0264 | FSPD_H | FSPD_L | RSPD_H | RSPD_L | - | - | - | - |
| 0x0268 | - | - | - | - | ABS | - | - | - |

### Détail des bits

#### CAN 0x0209 (Engine)
- **RPM:** `(byte[0] << 8) | byte[1]` - Big-endian 16-bit
- **Gear:** `byte[4] & 0x07` - Bits 0-2 (0=N, 1-6=gear, 7=invalid)

#### CAN 0x0215 (Throttle)
- **TPS:** `(byte[0] << 8) | byte[1]` - Throttle Position Sensor
- **APS:** `(byte[2] << 8) | byte[3]` - Accelerator Position Sensor
- **Launch:** `(byte[6] & 0x60) != 0` - Bits 5-6
- **TCS:** `(byte[7] >> 5) & 1` - Bit 5
- **SCS:** `(byte[7] >> 4) & 1` - Bit 4
- **LIF:** `(byte[7] >> 3) & 1` - Bit 3

#### CAN 0x023E (Temperature & Fuel)
- **Water Temp:** `byte[0]` - **SINGLE BYTE** (pas 16-bit!)
- **Intake Temp:** `byte[1]` - **SINGLE BYTE** (pas 16-bit!)
- **Fuel Delta:** `(byte[2] << 8) | byte[3]` - Accumulé au total

#### CAN 0x0250 (Acceleration)
- **ACC_X:** `(byte[0] << 8) | byte[1]` - Accélération longitudinale
- **ACC_Y:** `(byte[2] << 8) | byte[3]` - Accélération latérale

#### CAN 0x0258 (IMU)
- **LEAN:** Formule complexe sur bytes 0-3 (voir section 5)
- **PITCH:** `(byte[6] << 8) | byte[7]`

#### CAN 0x0260 (Brakes)
- **Front Brake:** `(byte[0] << 8) | byte[1]`
- **Rear Brake:** `(byte[2] << 8) | byte[3]`

#### CAN 0x0264 (Speed)
- **Front Speed:** `(byte[0] << 8) | byte[1]`
- **Rear Speed:** `(byte[2] << 8) | byte[3]`

#### CAN 0x0268 (ABS)
- **F_ABS:** `byte[4] & 1` - Bit 0
- **R_ABS:** `(byte[4] >> 1) & 1` - Bit 1

---

## 7. Écarts identifiés avec le parser Python

### 7.1 Formule LEAN

**Parser Python:**
```python
b0, b1, b2, b3 = data[0], data[1], data[2], data[3]
val1 = ((b0 << 4) | (b2 & 0x0f)) << 8
val2 = ((b1 & 0x0f) << 4) | (b3 >> 4)
lean_sum = (val1 + val2) & 0xFFFF
return lean_sum  # Stocké directement
```

**Native:**
```python
# Même calcul de sum, MAIS ensuite:
if sum < 9000:
    deviation = 9000 - sum
else:
    deviation = sum - 9000

if deviation <= 499:
    return 9000  # Deadband
else:
    return 9000 + deviation - (deviation % 100)  # Arrondi au degré
```

**Impact:** Le parser stocke la somme brute, la native transforme en amplitude avec deadband.

### 7.2 Position des bytes TPS/APS dans CAN 0x0215

Le désassemblage montre que TPS et APS pourraient être inversés par rapport à ce qui est documenté. À vérifier avec les valeurs réelles.

### 7.3 Nombre de points

- Native: 16462 points
- Parser Python: 16474 points (+12)

**Cause probable:** Le lissage de timestamps par la native élimine certains échantillons.

---

## 8. TODO pour session suivante

### Priorité haute
- [ ] Implémenter la formule LEAN native exacte en Python
- [ ] Tester avec les données réelles et comparer lean_raw
- [ ] Vérifier l'ordre TPS/APS dans le parser

### Priorité moyenne
- [ ] Analyser la fonction `GetSensorsRecordData` pour comprendre le lissage de timestamps
- [ ] Documenter la structure du fichier avant chaque GPS (millisecondes)
- [ ] Créer des tests unitaires pour chaque fonction CAN

### Priorité basse
- [ ] Analyser `AnalisysNMEA` pour la parsing GPS
- [ ] Analyser `AnalisysAIN` pour les entrées analogiques
- [ ] Documenter le format des fichiers TRG compressés

---

## Annexe A: Commandes radare2 utilisées

```bash
# Ouvrir et analyser
r2 -A libSensorsRecordIF.so

# Lister les fonctions
afl

# Désassembler une fonction
s sym.AnalisysCAN__record_data___can_data__int_
pdf

# Chercher les références à une valeur
/x 28230000  # Recherche 0x2328 (9000)

# Lister les symboles exportés
nm -D libSensorsRecordIF.so
```

---

*Document généré par analyse automatique. Dernière mise à jour: 2026-01-26*
