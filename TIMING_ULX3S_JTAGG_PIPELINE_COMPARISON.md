# ULX3S JTAGG: Pipeline-Vergleich

Messung vom 2026-07-22 für `::bonfire-core-soc:0`, Target
`ulx3s_jtagg`, mit `fw_monitor`, ECP5-85K/CABGA381, Speed Grade 6 und der
projektlokalen OSS-CAD-Toolchain (Yosys 0.67). Der LPF-Constraint beträgt
25 MHz; alle Varianten erfüllen ihn.

## Ergebnisse

| Konfiguration | Sysclk-Fmax | LUT4 | TRELLIS_FF | `hazards.S` bis Monitor-Pass |
|---|---:|---:|---:|---:|
| 3 Stufen | **81,39 MHz** | 3.060 | 1.620 | 230 Takte |
| 4 Stufen, historisches Shared-Result, Bypass an | 78,36 MHz | 3.017 | 1.654 | 230 Takte |
| 4 Stufen, historisches Shared-Result, Bypass aus | 81,07 MHz | 2.832 | 1.654 | 253 Takte |
| 4 Stufen, Quellenregister, Bypass an | **82,93 MHz** | 3.034 | 1.754 | 230 Takte |
| 4 Stufen, Quellenregister, Bypass aus | 80,43 MHz | **2.740** | 1.754 | 253 Takte |

Gegenüber drei Stufen bedeutet das:

- Vier Stufen mit Bypass: −3,03 MHz (−3,7 %), 43 LUT4 weniger und 34 FF
  mehr; keine zusätzliche Laufzeit im gezielten Hazard-Test.
- Vier Stufen ohne Bypass: −0,32 MHz (−0,4 %), 228 LUT4 weniger und 34 FF
  mehr; wegen RAW-Interlocks 23 zusätzliche Takte (+10,0 %).
- Quellenregister mit registrierter One-Hot-Auswahl kosten gegenüber dem
  bisherigen Vier-Stufen-Backend 100 FF. Die vier Datenregister werden ohne
  vorgeschaltete Ladeauswahl direkt von den Funktionseinheiten gespeist.
  Ohne Bypass sinkt Fmax in diesem Einzelaufbau um 0,64 MHz; mit Bypass steigt
  sie um 4,57 MHz. Da das Target keinen festen Seed verwendet, bleibt der
  Abstand trotz dieser deutlichen Verbesserung eine Einzelmessung; die
  Variante wird deshalb noch nicht als Target-Default gesetzt.

Die Fmax-Werte sind jeweils der letzte Sysclk-Wert aus `next.log` nach dem
vollständigen Routing. Die Ressourcenwerte stammen aus der abschließenden
Yosys-Zellstatistik.

## Ausführungsmessung

`code/core-tests/hazards.S` enthält direkte Producer-Consumer-Folgen für
ALU, Shifter, Load, Store, Branch, CSR sowie JAL/JALR. Die MyHDL-Clock hat
eine Periodendauer von 10; Monitor-Schreibzugriffe liegen auf steigenden
Flanken.

| Konfiguration | Monitor-Zeitstempel | Taktzahl |
|---|---:|---:|
| 3 Stufen | `@2295` | 230 |
| 4 Stufen, Bypass an | `@2295` | 230 |
| 4 Stufen, Bypass aus | `@2525` | 253 |
| 4 Stufen, Quellenregister, Bypass an | `@2295` | 230 |
| 4 Stufen, Quellenregister, Bypass aus | `@2525` | 253 |

Die Taktzahl ist `(Zeitstempel + 5) / 10`, weil die erste steigende Flanke
bei Zeit 5 liegt.

## Warum ist die Drei-Stufen-Fmax auf ULX3S höher als auf IcePi Zero?

Der Vergleich bezieht sich auf die aktuelle Messung in
`TIMING_ICEPIZERO_JTAGG_PIPELINE_COMPARISON.md`: IcePi Zero erreicht mit
derselben Drei-Stufen-Architektur 69,81 MHz, ULX3S 81,39 MHz. Der Engpass ist
in beiden Fällen derselbe strukturelle Pfad:

```text
SoC-BRAM-DOB -> LoadStoreUnit rdmux_out -> ls_result_o-FF
```

| Target | Gesamtdelay | Logik | Routing |
|---|---:|---:|---:|
| IcePi Zero, ECP5-25K | 14,32 ns | 8,29 ns | 6,03 ns |
| ULX3S, ECP5-85K | 12,29 ns | 7,45 ns | 4,84 ns |

Der Unterschied von 2,03 ns erklärt die Fmax-Differenz. Insbesondere sind
auf dem 85K sowohl die BRAM-zu-LUT-Verbindung als auch die anschließende
Load-Formatierungslogik günstiger gepackt und geroutet. Der ULX3S-Pfad hat
1,19 ns weniger Routing- und 0,84 ns weniger Logikdelay.

Das ist keine andere Drei-Stufen-Core-Architektur: Beide Pfade enden am
LoadStore-Resultatregister. Die wesentlichen Unterschiede sind das
physische Target (85K statt 25K), die resultierende Platzierung/Packing-Form
und geringfügig verschiedene, plattformabhängige `monitor.hex`-Inhalte.

## Reproduktionsbedingungen und Einschränkung

Jede Konfiguration wurde in einem eigenen frischen Build-Root erzeugt. Es
wurden nur `pipeline_length` und `writeback_bypass` geändert; JTAGG,
`jump_bypass: false`, Firmware und Toolchain waren innerhalb des ULX3S-
Vergleichs identisch.

Die Quellenregister-Läufe bilden die aktuelle Vier-Stufen-Implementierung
ab; die Shared-Result-Zeilen sind historische Vergleichsmessungen. Sie wurden
in temporären Build-Roots erzeugt, ohne die lokale Target-Datei zu verändern.

Das ULX3S-Target setzt keinen festen nextpnr-Seed. Die Werte sind daher
Einzelmessungen; kleine Unterschiede können Placement-Schwankungen
enthalten. Für belastbare Feindifferenzen sollte ein fixer Seed gesetzt und
mehrfach gemessen werden.
